from exceptions import MissingParameterError, MissingFileError  
from helpers.modelsUtils import REGISTRO_MODELOS

def get_p_handler(modelo):
    config = REGISTRO_MODELOS.get(modelo)
    return config["params"] if config else None


class ParametersHandler:
    parametros_objetivo = []
    defaults = {}    # Valor si no existe en el CSV
    hardcoded = {}   # Valor siempre, ignore el CSV

    complete_fuel_csv = None
    path_csv_tmp = None

    def get_parameters(self, meteo_data, index_map):
        raise NotImplementedError

    def get_formated(self):
        header = ";".join(self.parametros_objetivo) + "\n"
        rows = []
        
        try:
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
                        float(parts[colum_map["Index"]])
                    except (ValueError, KeyError):
                        continue

                    row_values = []
                    for param in self.parametros_objetivo:
                        if param in self.hardcoded:
                            value = self.hardcoded[param]
                        elif param in colum_map:
                            value = parts[colum_map[param]]
                        elif param in self.defaults:
                            value = self.defaults[param]
                        else:
                            raise MissingParameterError(param)

                        value = self.post_process(param, value)
                        row_values.append(str(value))

                    rows.append(";".join(row_values))
          
        except (FileNotFoundError, TypeError):
            raise MissingFileError(self.complete_fuel_csv)
        
        parameters = header + "\n".join(rows)
        with open(self.path_csv_tmp, 'w', encoding='utf-8') as f_out:
            f_out.write(parameters)

        return parameters

    #Este método permite cambiar parametros concretos en condiciones concretas en cada hijo
    def post_process(self, param, value):
        return value
    

    