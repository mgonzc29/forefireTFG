from netCDF4 import Dataset
import numpy as np
import rasterio
from rasterio.features import rasterize
from rasterio.windows import from_bounds
from rasterio.warp import transform
from rasterio.transform import rowcol
from scipy.ndimage import zoom 
from shapely.geometry import Point, LineString, Polygon
from affine import Affine

def get_r_handler(modelo):
    from BalbiNov2011.rasterHandlerBalbiNov2011 import RasterHandlerBalbiNov2011
    #from Farsite.rasterHandlerFarsite import RasterHandlerFarsite
    modelos = {
        #"Farsite": RasterHandlerFarsite(),
        "BalbiNov2011": RasterHandlerBalbiNov2011(),
        "BalbiNov2011TMdMl": RasterHandlerBalbiNov2011()
    }
    return modelos.get(modelo)

class RasterHandler:
    def __init__(self):
        pass


    def get_netCDF(self, meteo_data, center_coords, radius, firewallsGeometry=None):

        wind_layer, moisture_layer, temperature_layer, fuel_layer, altitude_layer, win_convert, crs, bounds = self.preprocess_raster_netCDF(meteo_data, center_coords, radius)
        
        if firewallsGeometry is not None:
            fwGeom = self.convert_geometry(firewallsGeometry,'EPSG:4326',crs, win_convert)
            fuel_layer = self.set_firewall(fuel_layer,fwGeom)
        netCDF_path, crs_bounds, index_map = self.build_netCDF(fuel_layer, altitude_layer, wind_layer, moisture_layer, temperature_layer, crs, bounds)
        return netCDF_path, crs_bounds, index_map
    
    def preprocess_raster_netCDF(self, meteo_data, center_coords, radius):
        # Devuelve fuel_layer, altitude_layer, wind_layer, moisture_layer, temperature_layer, crs, bounds
        raise NotImplementedError("Implementado en subclase")
    
    def get_wind_components(self, wind_speed, wind_direction):
        t_steps = len(wind_speed)
    
        wind_speed = np.array(wind_speed)
        wind_direction = np.radians(np.array(wind_direction))  # Convertir a radianes

        u_component = -wind_speed * np.sin(wind_direction)  # Componente u (este-oeste)
        v_component = -wind_speed * np.cos(wind_direction)  # Componente v (norte-sur)

        return np.stack([u_component, v_component]).reshape(2, t_steps, 1, 1)

    def get_wind_from_tif(self,uWindTif, vWindTif, x, y, radio):
        wind=[]

        if (uWindTif and vWindTif):
            uWindZoneTif= self.get_zone_over_coord(uWindTif,x,y,radio)
            wind.append(uWindZoneTif[:][0])
            vWindZoneTif= self.get_zone_over_coord(vWindTif,x,y,radio)
            wind.append(vWindZoneTif[:][0])
            wind=np.array(wind)
        else:
            wind= self.get_default_wind()

    def get_zone_over_coord(self, archivotif, lon, lat, coord_system, radio):
        #solo lee los tif que vengan en utm
        with rasterio.open(archivotif) as src:  
            x,y = self.convert_coord(lon, lat, coord_system, src.crs)
            left = x - radio
            right = x + radio
            bottom = y - radio
            top = y + radio
            

            if src.crs.is_geographic:
                left, right, bottom, top = self.get_origin_geo(src.crs, left, bottom, right, top)

            window = from_bounds(left, bottom, right, top, src.transform)
            
            data = src.read(window=window, boundless=True, fill_value=0).astype(np.float32)
            nodata_val = src.nodata
            if nodata_val is not None:
                data[data == nodata_val] = np.nan

            if src.transform[4] < 0:
                data = np.flip(data, axis=1)
                orig_win_transform = src.window_transform(window)
                win_transform = Affine(orig_win_transform.a, 0, left,0, abs(orig_win_transform.e), bottom)
            else:
                win_transform = src.window_transform(window)

            bounds = (left, bottom, right, top)


            # out_meta = src.meta.copy()
            # with rasterio.open("nombre_salida", "w", **out_meta) as dest:
            #     dest.write(data)

            return data, win_transform, src.crs, bounds
        
    def get_origin_geo(self, crs, W, S, E, N):
        lons, lats = transform(crs, {'init': 'EPSG:4326'}, [W, E], [S, N])    
        return lats[0], lats[1], lons[0], lons[1]
    
    def convert_coord(self, lon, lat, originCRS, targetCRS, win_transform=None):
        new_lons, new_lats = transform(originCRS, targetCRS, [lon], [lat])
        new_lon, new_lat= new_lons[0], new_lats[0]
        if win_transform is not None:
            new_lat,new_lon = rowcol(win_transform, new_lon, new_lat)
        return new_lon, new_lat
    
    def convert_geometry(self, geometry, originCRS, targetCRS,transform=None):
        new_geometry = []
        
        for poligon in geometry:
            new_pol = []
            for point in poligon:
                # Usamos tu método existente para cada par de coordenadas
                new_x, new_y = self.convert_coord(point[0], point[1], originCRS, targetCRS, transform)
                new_pol.append([new_x, new_y])
            new_geometry.append(new_pol)
            
        return new_geometry

    #0 para vecino mas cercano y 1 para bilineal
    def resize_layer(self, map, target_shape, resample_method):
        a=map.shape[:-2]
        fullTarget = map.shape[:-2] + target_shape
        zoomFactors = [t / m for t, m in zip(fullTarget, map.shape)]
        return zoom(map, zoomFactors, order=resample_method)

    def set_firewall(self, fuel_layer, geometry):
        alto, ancho = fuel_layer.shape
        firewalls_shapely = []
        grosor=2
        for poligon in geometry:
            n_puntos = len(poligon)
            
            if n_puntos == 1:
                # Punto
                firewalls_shapely.append(Point(poligon[0]).buffer(grosor))
            elif n_puntos >= 3 and poligon[0] == poligon[-1]:
                # Polígono
                firewalls_shapely.append(Polygon(poligon))
            else:
                # Es una Línea (2 o más puntos no cerrados)
                firewalls_shapely.append(LineString(poligon).buffer(grosor))

        # Se crea máscara: 0 donde hay cortafuegos, 1 donde no
        mask = rasterio.features.rasterize(
            [(geom, 0) for geom in firewalls_shapely],
            out_shape=(alto, ancho),
            fill=1,
            all_touched=True
        )
        return fuel_layer * mask

    def build_netCDF(self, fuel_layer, altitude_layer, wind_layer, moisture_layer, temperature_layer, crs, bounds):
        target_shape = fuel_layer.shape
        W, S, E, N = bounds
        minLat, maxLat, minLon, maxLon = self.get_origin_geo(crs, W, S, E, N)
        alto, ancho = target_shape

        altitude_layer = self.resize_layer(altitude_layer, target_shape, resample_method=0)
        fuel_layer, index_map = self.adapt_fuel_indexes(fuel_layer)

        lx = E - W
        ly = N - S

        aux_path= "data/temp/aux.nc"

        nc = Dataset(aux_path, "w", format="NETCDF4")

        nc.createDimension("ft", 1)
        nc.createDimension("fz", 1)
        nc.createDimension("fy", alto)
        nc.createDimension("fx", ancho)
        nc.createDimension("nt", 1)
        nc.createDimension("nz", 1)
        nc.createDimension("ny", alto)
        nc.createDimension("nx", ancho)

        #nc.createDimension("time", nt_wind)
        nc.type = "domain"

        #Dominio
        domain = nc.createVariable("domain", "i4")
        domain.assignValue(0)
        domain.SWx = np.float32(0)
        domain.SWy = np.float32(0)
        domain.Lx = np.float32(lx)
        domain.Ly = np.float32(ly)
        domain.BBoxWSEN = f"{minLon},{minLat},{maxLon},{maxLat}"
        domain.Lz = np.float32(0.0)
        domain.SWz = np.float32(0.0)
        domain.type = "domain"
        domain.WSENLBRT = f"{minLon},{minLat},{maxLon},{maxLat},0.0,0.0,{lx},{ly}"
        domain.t0 = np.float32(0.0)  
        domain.Lt = np.float32("inf") 

        # Capas Estáticas
        fuel = nc.createVariable("fuel", "i2", ("ft", "fz", "fy", "fx"))
        fuel.type = "fuel"
        fuel[0, 0, :, :] = (fuel_layer).astype(np.int16)

        altitude = nc.createVariable("altitude", "i2", ("nt", "nz", "ny", "nx"))
        altitude.type = "data"
        altitude[0, 0, :, :] = altitude_layer.astype(np.float32)

        intervaloDatos=1800
        t_final = float((wind_layer[0].shape[0]) * intervaloDatos)
        domain.Lt = np.float32(t_final)
        nc.createDimension("wt", wind_layer[0].shape[0])

        if(wind_layer is not None):
            wind_layer = self.resize_layer(wind_layer, target_shape, resample_method=1)
            
            windU = nc.createVariable("windU", "f4", ("wt", "nz", "ny", "nx"))
            windU.type = "data"
            windU.interval = np.float32(intervaloDatos)
            windU.Lt = float(t_final)
            windU.t0 = float(0.0)
            windU[:, 0, :, :] = wind_layer[0].astype(np.float32)

            windV = nc.createVariable("windV", "f4", ("wt", "nz", "ny", "nx"))
            windV.type = "data"
            windV.interval = np.float32(intervaloDatos)
            windV.Lt = float(t_final)
            windV.t0 = float(0.0)
            windV[:, 0, :, :] = wind_layer[1].astype(np.float32)
        
        if(moisture_layer is not None):
            moisture_layer = self.resize_layer(moisture_layer, target_shape, resample_method=1)
            moisture = nc.createVariable("moisture", "f4", ("wt", "nz", "ny", "nx"))
            moisture.type = "data"
            moisture.Lt = float(t_final)
            moisture.t0 = float(0.0)
            moisture[:, 0, :, :] = moisture_layer[0].astype(np.float32)

        if(temperature_layer is not None):
            temperature_layer = self.resize_layer(temperature_layer, target_shape, resample_method=1)
            temperature = nc.createVariable("temperature", "f4", ("wt", "nz", "ny", "nx"))
            temperature.type = "data"
            temperature.Lt = float(t_final)
            temperature.t0 = float(0.0)
            temperature[:, 0, :, :] = temperature_layer[0].astype(np.float32)
            
        nc.close()

        return aux_path, (minLon, minLat, maxLon, maxLat), index_map
    
    #fuel_layer tiene que ser un np.array
    def adapt_fuel_indexes(self, fuel_layer):
        valores_unicos = np.unique(fuel_layer[fuel_layer != 0])  
        index_map = {0: 0}
        for i, val in enumerate(valores_unicos):
            index_map[int(val)]= i + 1 
    
        nueva_matriz = np.vectorize(index_map.get)(fuel_layer)
        return nueva_matriz, index_map
