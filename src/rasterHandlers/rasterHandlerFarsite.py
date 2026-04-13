from pathlib import Path
from netCDF4 import Dataset
from rasterHandler import RasterHandler
import numpy as np
from helpers.preprocessUtils import join_parameters_tif

class RasterHandlerFarsite(RasterHandler):

    altitude_tif= Path("data/rasters/Multiband_Espanhia.tif")
    
    def preprocess_raster_netCDF(self, meteo_data, center_coords, radius):

        open_zone_tif_multiband=self.get_zone_over_coord(self.altitude_tif,center_coords[0], center_coords[1], 'EPSG:4326', radius) 
        
        altitude_layer = open_zone_tif_multiband[0][0]
        fuel_layer = open_zone_tif_multiband[0][3]
        fuel_layer = fuel_layer #Ajuste 

        win_transform = open_zone_tif_multiband[1]
        crs = open_zone_tif_multiband[2]
        bounds = open_zone_tif_multiband[3]

        wind_layer=self.get_wind_components(meteo_data[2], meteo_data[3])
        moisture_layer=None
        temperature_layer=None
        #to do: ver como recibe moist.parametros
        return wind_layer, moisture_layer, temperature_layer, fuel_layer, altitude_layer, win_transform, crs, bounds
    