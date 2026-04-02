def get_p_handler(modelo):
    from BalbiNov2011.parametersHandlerBalbiNov2011 import ParametersHandlerBalbiNov2011
    from Farsite.parametersHandlerFarsite import ParametersHandlerFarsite
    modelos = {
        #"Farsite": ParametersHandlerFarsite(),
        "BalbiNov2011": ParametersHandlerBalbiNov2011(),
        "BalbiNov2011TMdMl": ParametersHandlerBalbiNov2011()
    }
    return modelos.get(modelo)


class ParametersHandler:
    def __init__(self):
        pass
    
    def get_parameters(self, meteo_data, index_map):
        raise NotImplementedError("Implementado en subclase")
    

#Para implementar más modelos de propagación se deben definir nuevas clases hijas de modelParameterHandler
    

    