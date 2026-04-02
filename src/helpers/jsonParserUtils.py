import json

def get_meteo_data_from_file(meteo_json_path):
    try:
        with open(meteo_json_path, 'r') as archivo:
            datos = json.load(archivo)
            temp = None
            humidity = None
            wind_speed = None
            wind_direction = None
            
            for item in datos:
                variable_id = item["ID"]
                valores = item["VALORES"]

                match variable_id:
                    case "temperatura":
                        temp=valores
                    
                    case "humedad":
                        humidity=valores
                    
                    case "viento":
                        wind_speed=valores
                    
                    case "direccionViento":
                        wind_direction=valores
    except Exception as e:
        return None, None, None, None
    return temp, humidity, wind_speed, wind_direction

def get_meteo_data_from_string(meteo_json_string):
    try:
        datos = json.loads(meteo_json_string)
        temp = None
        humidity = None
        wind_speed = None
        wind_direction = None
            
        for item in datos:
            variable_id = item["ID"]
            valores = item["VALORES"]

            match variable_id:
                case "temperatura":
                    temp=valores
                
                case "humedad":
                    humidity=valores
                
                case "viento":
                    wind_speed=valores
                
                case "direccionViento":
                    wind_direction=valores
    except Exception as e:
        return None, None, None, None
    return temp, humidity, wind_speed, wind_direction