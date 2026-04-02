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
    
    def get_parameters(self, meteo_data, index_map):
        join_parameters_csv(self.model_csv, self.plant_csv, self.complete_fuel_csv, index_map)
        return self.get_formated(sum(meteo_data[0])/len(meteo_data[0])+273.15, index_map)

    def get_formated(self, temp_kelvin, index_map):
        parametros_objetivo = ["Index", "Rhod", "Rhol", "Md", "Ml", "sd", "sl", "e","Sigmad", "Sigmal", "stoch", "RhoA", "Ta", "Tau0","Deltah", "DeltaH", "Cp", "Cpa", "Ti", "X0", "r00", "Blai","me"]
        
        header = ";".join(parametros_objetivo) + "\n"
        rows = []
        
        with open(self.complete_fuel_csv, 'r') as f:
            primera_linea = f.readline()
            if not primera_linea:
                return ""
            colum_map = {nombre: i for i, nombre in enumerate(primera_linea.strip().split(','))}
            
            for line in f:
                parts = line.strip().split(',')
                
                if not parts or not parts[0].replace('.', '', 1).isdigit():
                    continue
                try:
                    f_id = float(parts[colum_map.get("Index")])
                except (ValueError, KeyError):
                    continue
                rhod = parts[colum_map.get("Rhod")]   
                rhol = parts[colum_map.get("Rhol")]   
                md = parts[colum_map.get("Md")]     
                ml = parts[colum_map.get("Ml")]   
                sd = parts[colum_map.get("sd")]     
                sl = parts[colum_map.get("sl")]    
                e = parts[colum_map.get("e")]      
                sigmad = parts[colum_map.get("Sigmad")] 
                sigmal = parts[colum_map.get("Sigmal")]
                tau0 = parts[colum_map.get("Tau0")]  
                deltah = parts[colum_map.get("Deltah")] 
                deltaH = parts[colum_map.get("DeltaH")] 
                me = parts[colum_map.get("me")] 
                
                stoch = parts[colum_map.get("stoch")]  if "stoch"  in colum_map else "8.3"
                rhoa = parts[colum_map.get("RhoA")]  if "RhoA" in colum_map else "1.2" 
                ta = parts[colum_map.get("Ta")]     if "Ta"     in colum_map else temp_kelvin 
                cp = parts[colum_map.get("Cp")]   if "Cp" in colum_map else "1800"   
                cpa = parts[colum_map.get("Cpa")]    if "Cpa"    in colum_map else "1005"
                ti = parts[colum_map.get("Ti")]  if "Ti" in colum_map else 600
                x0 = parts[colum_map.get("X0")] if "X0" in colum_map else "0.3"
                r00 = parts[colum_map.get("r00")] if "r00" in colum_map else "2.5e-05"
                blai = parts[colum_map.get("Blai")]  if "Blai" in colum_map else "4"
                me = parts[colum_map.get("me")]  if "me" in colum_map else "0.1"

                #Valores constantes/hardcodeados
                if sigmal == "0.0":
                    sigmal = "0.1"
                ml=0.8
                md=0.1
                r = f"{f_id};{rhod};{rhol};{md};{ml};{sd};{sl};{e};{sigmad};{sigmal};{stoch};{rhoa};{ta};{tau0};{deltah};{deltaH};{cp};{cpa};{ti};{x0};{r00};{blai};{me}"
                
                rows.append(r)
                parameters = header + "\n".join(rows)  

                
                with open(self.path_csv_tmp, 'w', encoding='utf-8') as f_out:
                    f_out.write(parameters)                 
        
        return parameters
    
 