from datetime import datetime
import os
import pyforefire as forefire
from ddtrace import tracer

from exceptions import InvalidInputError, SimulationPreProcessingError, UnsupportedZoneError
from helpers.jsonParserUtils import get_meteo_data_from_file, get_meteo_data_from_string
from rasterHandler import get_r_handler
from parametersHandler import get_p_handler

class Simulator:

    @tracer.wrap("create_simulator", resource="create_simulator")
    def __init__(self,model,dump_mode):

        self.model=model
        self.dump_mode=dump_mode
        self.ff = forefire.ForeFire()
        self.p_handler = get_p_handler(model)
        self.r_handler = get_r_handler(model)
        if not self.p_handler or not self.r_handler:
            raise InvalidInputError(f"Modelo '{model}' no soportado.")
        if self.dump_mode not in ["json", "kml", "ff", "geojson"]:
            raise InvalidInputError("dump_mode debe ser 'json', 'kml', 'ff' o 'geojson'")

        with tracer.trace("set_configuration", resource="set_configuration") as span:
            self.set_configuration()

    #Esta función es el punto de acceso desde la API
    #geometry tiene varios elementos que pueden tener uno o varias coordenadas
    #dateTime en formato: YYYY-MM-DDTHH:MM:SSZ
    #meteo_data es un json con los datos meteorológicos (no un path, el contenido)
    @tracer.wrap("simulate", resource="simulate_forefire")
    def simulate(self, geometry, init_date_time, end_date_time, interval, meteo_data, firewalls = None):
        span = tracer.current_span()
        if span:
            span.set_tag("model", self.model)
            span.set_tag("init_date_time", init_date_time)
            span.set_tag("end_date_time", end_date_time)
            span.set_tag("interval", interval)
            span.set_tag("dump_mode", self.dump_mode)
        
        #Comprobaciones de datos recibidos
        if not geometry or not any(geometry):
            raise InvalidInputError("Geometría vacía o sin puntos válidos")
        if end_date_time <= init_date_time:
            raise InvalidInputError("end_date_time debe ser posterior a init_date_time")
        if interval <= 0:
            raise InvalidInputError("El intervalo debe ser positivo")
    
        meteo_data = get_meteo_data_from_string(meteo_data) #(temp, humidity, wind_speed, wind_direction)

        center_coords = self.get_center_point(geometry)
        radius=2000 #radio estandar para nuestras simulaciones

        with tracer.trace("build_netCDF", resource="build_netCDF") as span:
            span.set_tag("center_coords", center_coords)
            span.set_tag("radius", radius)
            
            try:
                netCDF_path, domain_bounds, index_map = self.r_handler.get_netCDF(meteo_data, center_coords, radius, firewalls)
            except UnsupportedZoneError:
                raise
            except Exception as e:
                span.set_tag("error", str(e))
                raise SimulationPreProcessingError(f"Error al construir el netCDF: {e}")

        with tracer.trace("format_fuel_parameters", resource="format_fuel_parameters") as span:
            try:
                parameter = self.p_handler.get_parameters(meteo_data, index_map)
            except Exception as e:
                    span.set_tag("error", str(e))
                    raise SimulationPreProcessingError(f"Error al formatear los parámetros de combustible: {e}")
            
        with tracer.trace("load_fuel_parameters", resource="load_fuel_parameters") as span:
            self.ff["fuelsTable"] = parameter

        with tracer.trace("load_netCDF", resource="load_netCDF") as span:
            self.ff.execute(f"loadData[{netCDF_path};{init_date_time}]") 

        with tracer.trace("start_fire", resource="start_fire") as span:
            span.set_tag("geometry", geometry)
            self.start_fire(geometry, radius, domain_bounds,center_coords)
        
        with tracer.trace("run_simulation", resource="run_simulation") as span:
            n_steps = self.get_n_steps(init_date_time, end_date_time, interval)
            if n_steps <= 0:
                span.set_tag("error", "Número de pasos de simulación no válido (init, end e interval no congruentes)")
                raise InvalidInputError("Número de pasos de simulación no válido (init, end e interval no congruentes)")
            results=self.get_simulation_results(n_steps,interval ,True)
        return results
        
    #to do: no le hace gracia si es solo un punto
    #geometry shape = (Nº de frentes, Nº de focos por frente)
    #to do: cambiar para que use el transform
    def start_fire(self,geometry, radius, bounds, center_coords):
        W, S, E, N = bounds
        diameter = radius * 2
        cx = ((center_coords[0] - W) / (E - W)) * diameter
        cy = ((center_coords[1] - S) / (N - S)) * diameter

        for i,front in enumerate(geometry):
            self.ff.execute(f"    FireFront[id={i};domain=0;t=0]")
            for j,node in enumerate(front):
                n_x = ((node[0] - W) / (E - W)) * diameter
                n_y = ((node[1] - S) / (N - S)) * diameter
                self.ff.execute(f"        FireNode[domain=0;id={j};loc=({n_x},{n_y},0);vel=(0,0,0);t=0;state=init;frontId={i}]")

    def get_n_steps(self, init_date_time, end_date_time, interval):
        init_dt = datetime.fromisoformat(init_date_time.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_date_time.replace('Z', '+00:00'))
        duration = end_dt - init_dt
        n_steps = duration.seconds / interval
        return int(n_steps)

    def set_configuration(self):
        self.ff["ForeFireDataDirectory"] = "."
        self.ff["propagationModel"] = self.model
        self.ff["dumpMode"] = self.dump_mode

        #to do: decidir que hacer con ellos:
        self.ff["perimeterResolution"] = 10
        self.ff["spatialIncrement"] = 3
        self.ff["propagationSpeedAdjustmentFactor"] = 0.6
        self.ff["windReductionFactor"] = 0.4

    def get_simulation_results(self,n_steps,interval, verbose=False):
        results=[]

        run=build_runs_directory(self.model)
        os.makedirs(os.path.join(run, f"state"))
        
        self.ff.execute(f'print[{run}/simulationResult0.{self.dump_mode}]')
        results.append(f"{run}/simulationResult0.{self.dump_mode}")
        if verbose:
                self.ff["dumpMode"] = "ff"
                self.ff.execute(f'print[{run}/state/t0.ff]')
                self.ff["dumpMode"] = self.dump_mode
        for i in range(1,n_steps+1):
            self.ff.execute("step[dt=%f]" % interval)
            self.ff.execute(f'print[{run}/simulationResult{i}.{self.dump_mode}]')
            results.append(f"{run}/simulationResult{i}.{self.dump_mode}")
            if verbose:
                self.ff["dumpMode"] = "ff"
                self.ff.execute(f'print[{run}/state/t{i}.ff]')
                self.ff["dumpMode"] = self.dump_mode
        return results
        
    def get_center_point(self,geometry):
        #calcular center point a falta de saber si se le va a pasar o no
        all_points = [point for polygon in geometry for point in polygon]
        if all_points:
            x_coords = [p[0] for p in all_points]
            y_coords = [p[1] for p in all_points]
            center_x = sum(x_coords) / len(x_coords)
            center_y = sum(y_coords) / len(y_coords)
            center_coords = [center_x, center_y]
        else:
            center_coords = [0, 0]
            
        return center_coords
        



#A PARTIR DE AQUI TODO ES TEMPORAL PARA PRUEBAS


    def prueba_simple(self, geometry, initDateTime, endDateTime, interval, meteo, firewalls = None):
        results=[]
        meteo_data = get_meteo_data_from_string(meteo) #(temp, humidity, wind_speed, wind_direction)

        p_handler = get_p_handler(self.model)
        r_handler = get_r_handler(self.model)

        center_coords = self.get_center_point(geometry)
        #radio por defecto
        radius = 5000

        netCDF_path, domain_bounds, index_map = r_handler.get_netCDF(meteo_data, center_coords, radius, firewalls)
        parameter = p_handler.get_parameters(meteo_data, index_map)
        
        self.ff["fuelsTableFile"] = "data/temp/parameters.csv"
        self.ff.execute(f"loadData[{netCDF_path};{initDateTime.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'}]")

        #self.start_fire(geometry, radius, domain_bounds,center_coords)
        self.ff.execute(f"startFire[lonlat=({center_coords[0]},{center_coords[1]}, 0);t=0]")
        #self.ff.execute("trigger[fuelType=wind;vel=(60.0,0.0,0.0);t=0]")
        #self.ff.execute(f"include[tmp/fire.ff]")
        n_steps = self.get_n_steps(initDateTime, endDateTime, interval)
        results=self.get_simulation_results(3,3600,True)

        self.ff.execute("clear[]")
        return results


def build_runs_directory(model,base_path="runs", prefijo="run_"):
    if not os.path.exists(f"{base_path}/{model}"):
        os.makedirs(f"{base_path}/{model}")
    
    ids = []
    for nombre in os.listdir(f"{base_path}/{model}"):
        if nombre.startswith(prefijo):
            try:
                numero = int(nombre.replace(prefijo, ""))
                ids.append(numero)
            except ValueError:
                pass
    
    siguiente_id = max(ids) + 1 if ids else 1
    
    nueva_carpeta = os.path.join(f"{base_path}/{model}", f"{prefijo}{siguiente_id}")
    os.makedirs(nueva_carpeta)
    
    return nueva_carpeta
    



