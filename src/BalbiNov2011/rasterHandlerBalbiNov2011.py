from pathlib import Path
from netCDF4 import Dataset
from rasterHandler import RasterHandler
import numpy as np
from helpers.preprocessUtils import join_parameters_tif

class RasterHandlerBalbiNov2011(RasterHandler):

    plant_tif = Path("data/rasters/especies.tif")
    model_tif = Path("data/rasters/modelos.tif")
    complete_fuel_tif = Path("data/rasters/join.tif")
    altitude_tif= Path("data/rasters/Multiband_Espanhia.tif")
    
    def preprocess_raster_netCDF(self, meteo_data, center_coords, radius):

        if not (self.complete_fuel_tif.exists() and self.complete_fuel_tif.stat().st_size > 0):
            if self.plant_tif.exists() and self.model_tif.exists():
                join_parameters_tif(self.plant_tif, self.model_tif, self.complete_fuel_tif)
            else:
                return #Error por falta de archivos
        open_zone_tif_fuel=super().get_zone_over_coord(self.complete_fuel_tif,center_coords[0], center_coords[1], 'EPSG:4326', radius)
        open_zone_tif_altitude=super().get_zone_over_coord(self.altitude_tif,center_coords[0], center_coords[1], 'EPSG:4326', radius) 
        
        fuel_layer = open_zone_tif_fuel[0][0]
        fuel_layer[np.isnan(fuel_layer)] = 0 
        altitude_layer= open_zone_tif_altitude[0][0]
        
        win_transform = open_zone_tif_fuel[1]
        crs = open_zone_tif_fuel[2]
        bounds = open_zone_tif_fuel[3]

        wind_layer=super().get_wind_components(meteo_data[2], meteo_data[3])
        moisture_layer=(np.array(meteo_data[1])*0.01).reshape(1, len(meteo_data[1]), 1, 1)
        temperature_layer=np.array(meteo_data[0]).reshape(1, len(meteo_data[0]), 1, 1)

        return wind_layer, moisture_layer, temperature_layer, fuel_layer, altitude_layer, win_transform, crs, bounds
    
        