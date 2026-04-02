from datetime import datetime
import os
import pyforefire as forefire
from pathlib import Path
from ddtrace import tracer

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
            raise ValueError(f"Modelo '{model}' no soportado.")
        if self.dump_mode not in ["json", "kml", "ff", "geojson"]:
            raise ValueError("dump_mode debe ser 'json', 'kml', 'ff' o 'geojson'")

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
            raise ValueError("Geometría vacía o sin puntos válidos")
        if end_date_time <= init_date_time:
            raise ValueError("end_date_time debe ser posterior a init_date_time")
        if interval <= 0:
            raise ValueError("El intervalo debe ser positivo")
    
        meteo_data = get_meteo_data_from_string(meteo_data) #(temp, humidity, wind_speed, wind_direction)

        center_coords = self.get_center_point(geometry)
        radius=2000 #radio estandar para nuestras simulaciones

        with tracer.trace("build_netCDF", resource="build_netCDF") as span:
            span.set_tag("center_coords", center_coords)
            span.set_tag("radius", radius)
            
            try:
                netCDF_path, domain_bounds, index_map = self.r_handler.get_netCDF(meteo_data, center_coords, radius, firewalls)
            except Exception as e:
                span.set_tag("error", str(e))
                raise RuntimeError(f"Error al construir el netCDF: {e}")

        with tracer.trace("format_fuel_parameters", resource="format_fuel_parameters") as span:
            try:
                parameter = self.p_handler.get_parameters(meteo_data, index_map)
            except Exception as e:
                    span.set_tag("error", str(e))
                    raise RuntimeError(f"Error al formatear los parámetros de combustible: {e}")
            
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
                span.set_tag("error", "Número de pasos de simulación no válido")
                raise ValueError("Número de pasos de simulación no válido")
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
        duration = end_date_time - init_date_time  
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

        run=crear_carpeta_run()
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
        






    def prueba_simple(self, geometry, initDateTime, endDateTime, interval, firewalls = None):
        results=[]

        meteo_json= Path("data/meteo.json")
        meteo_data = get_meteo_data_from_file(meteo_json) #(temp, humidity, wind_speed, wind_direction)

        p_handler = get_p_handler(self.model)
        r_handler = get_r_handler(self.model)

        center_coords = self.get_center_point(geometry)
        #radio por defecto
        radius = 5000

        netCDF_path, domain_bounds, index_map = r_handler.get_netCDF(meteo_data, center_coords, radius, firewalls)
        parameter = p_handler.get_parameters(meteo_data, index_map) ,
        
        self.ff["fuelsTableFile"] = "data/temp/parameters.csv"
        self.ff.execute(f"loadData[{netCDF_path};{initDateTime.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'}]")

        #self.start_fire(geometry, radius, domain_bounds,center_coords)
        self.ff.execute(f"startFire[lonlat=({center_coords[0]},{center_coords[1]}, 0);t=0]")
        #self.ff.execute("trigger[fuelType=wind;vel=(60.0,0.0,0.0);t=0]")
        #self.ff.execute(f"include[tmp/fire.ff]")
        n_steps = self.get_n_steps(initDateTime, endDateTime, interval)
        results=self.get_simulation_results(n_steps,interval,True)

        return results





def crear_carpeta_run(base_path="runs", prefijo="run_"):
    # 1. Asegurarse de que la carpeta base existe
    if not os.path.exists(base_path):
        os.makedirs(base_path)
    
    # 2. Listar carpetas existentes y extraer los IDs
    ids = []
    for nombre in os.listdir(base_path):
        if nombre.startswith(prefijo):
            try:
                # Extraemos el número después del prefijo
                numero = int(nombre.replace(prefijo, ""))
                ids.append(numero)
            except ValueError:
                pass # Ignora carpetas que no sigan el formato
    
    # 3. Determinar el siguiente ID
    siguiente_id = max(ids) + 1 if ids else 1
    
    # 4. Crear la nueva carpeta
    nueva_carpeta = os.path.join(base_path, f"{prefijo}{siguiente_id}")
    os.makedirs(nueva_carpeta)
    
    return nueva_carpeta
    



