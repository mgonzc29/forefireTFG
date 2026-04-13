from pathlib import Path
from parametersHandler import ParametersHandler
from helpers.preprocessUtils import join_parameters_csv

#Esto parte se podrá generalizar y meter al padre
class ParametersHandlerFarsite(ParametersHandler):

    #Archivos csv utilizados por este modelo
    complete_fuel_csv = Path("data/csv/fuelWeatherMap.csv")
    path_csv_tmp = Path("data/temp/parameters.csv")

    parametros_objetivo = ["Index","h1","h10","h100","lh","lw","dynamic","sav1","savlh","savlw","depth","xmext","heatd","heatl"]
    #to do implementar index_map para curar en salud
    def get_parameters(self, meteo_data, index_map=None):
        
        self.defaults = {
            "dynamic": "0",
            "sav1":    "2000",  # Superficie/Volumen muerto (valor promedio)
            "savlh":   "1500",  # Superficie/Volumen herbáceo vivo
            "savlw":   "1500",  # Superficie/Volumen leñoso vivo
            "depth":   "1.0",   # Profundidad del lecho de combustible (metros)
            "xmext":   "0.25",  # Humedad de extinción (25%)
            "heatd":   "18600",  # Calor combustibles muertos
            "heatl":   "18600"  # Calor combustibles vivos
        }

        self.hardcoded = {
        }

        return self.get_formated()

 