from rasterHandlers.rasterHandlerBalbiNov2011 import RasterHandlerBalbiNov2011
from rasterHandlers.rasterHandlerFarsite import RasterHandlerFarsite
from parametersHandlers.parametersHandlerBalbiNov2011 import ParametersHandlerBalbiNov2011
from parametersHandlers.parametersHandlerFarsite import ParametersHandlerFarsite

REGISTRO_MODELOS = {
    "Farsite": {
        "raster": RasterHandlerFarsite(),
        "params": ParametersHandlerFarsite()
    },
    "BalbiNov2011": {
        "raster": RasterHandlerBalbiNov2011(),
        "params": ParametersHandlerBalbiNov2011()
    },
    "BalbiNov2011TMdMl": {
        "raster": RasterHandlerBalbiNov2011(),
        "params": ParametersHandlerBalbiNov2011()
    },
    "Rothermel": {
        "raster": RasterHandlerBalbiNov2011(),
        "params": ParametersHandlerBalbiNov2011()
    }
}

def get_models():
    return list(REGISTRO_MODELOS.keys())