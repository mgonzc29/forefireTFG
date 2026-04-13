# parametersHandlers/exceptions.py

class FireSimulatorError(Exception):
    """Excepción base para toda la aplicación."""
    pass

# ERRORES DEL CLIENTE

class InvalidInputError(FireSimulatorError):
    def __init__(self, message="Los datos de entrada son invalidos o estan mal formados."):
        self.message = message
        super().__init__(self.message)

class UnsupportedZoneError(FireSimulatorError):
    def __init__(self, lat, lon):
        self.message = f"Zona no soportada para la simulacion con el modelo seleccionado. Coords: lat {lat}, lon {lon}"
        super().__init__(self.message)

# ERRORES DEL SISTEMA

class MissingParameterError(FireSimulatorError):
    def __init__(self, param_name):
        self.param_name = param_name
        self.message = f"Error interno: Falta el parametro obligatorio '{param_name}'."
        super().__init__(self.message)

class MissingFileError(FireSimulatorError):
    def __init__(self, file_path):
        self.file_path = file_path
        self.message = f"Error de configuración: No se pudo encontrar ningun archivo en: {file_path}"
        super().__init__(self.message)
    
class SimulationPreProcessingError(FireSimulatorError):
    def __init__(self, details):
        self.details = details
        self.message = f"Error en el tiempo de ejecucion (Pre-procesado): {details}"
        super().__init__(self.message)