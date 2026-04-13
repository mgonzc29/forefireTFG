from pathlib import Path
from parametersHandler import ParametersHandler
from helpers.preprocessUtils import join_parameters_csv

#Esto parte se podrá generalizar y meter al padre
class ParametersHandlerBalbiNov2011(ParametersHandler):

    #Archivos csv utilizados por este modelo
    plant_csv = Path("data/csv/especies.csv")
    model_csv = Path("data/csv/modelos.csv")
    complete_fuel_csv = Path("data/csv/join.csv")
    path_csv_tmp = Path("data/temp/parameters.csv")

    parametros_objetivo = [
        "Index", "Rhod", "Rhol", "Md", "Ml", "sd", "sl", "e","Sigmad", "Sigmal", "stoch", 
        "RhoA", "Ta", "Tau0","Deltah", "DeltaH", "Cp", "Cpa", "Ti", "X0", "r00", "Blai", "me"
    ]

    def get_parameters(self, meteo_data, index_map):
        join_parameters_csv(self.model_csv, self.plant_csv, self.complete_fuel_csv, index_map)
        temp_kelvin = sum(meteo_data[0]) / len(meteo_data[0]) + 273.15
        
        self.defaults = {
            "stoch": "8.3",
            "RhoA":  "1.2",
            "Cp":    "1800",
            "Cpa":   "1005",
            "Ti":    "600",
            "X0":    "0.3",
            "r00":   "2.5e-05",
            "Blai":  "4",
            "me":    "0.1",
        }

        self.hardcoded = {
            "Ta":    str(temp_kelvin),
            "Ml":     "0.8",
            "Md":     "0.1",
            "Sigmal": "0.1",
        }

        return self.get_formated()

#Este método permite cambiar parametros concretos en condiciones concretas en cada hijo
def post_process(self, param, value):
    if param == "Sigmal" and value == "0.0":
        return "0.1"
    return value
    
 