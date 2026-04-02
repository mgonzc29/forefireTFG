from parametersHandler import parametersHandler

class parametersHandlerFarsite(parametersHandler):
    def getFormated(self,rutaArchivo):
        parametrosObjetivo = ["Index","h1","h10","h100","lh","lw","dynamic","sav1","savlh","savlw","depth","xmext","heatd","heatl"]
        rows = []
        
        header = ";".join(parametrosObjetivo) + "\n"
        rows = []

        with open(rutaArchivo, 'r') as f:
            primera_linea = f.readline()
            if not primera_linea:
                return ""
            columMap = {nombre: i for i, nombre in enumerate(primera_linea.strip().split())}
            
            for line in f:
                parts = line.split()

                if not parts or not parts[0].replace('.', '', 1).isdigit():
                    continue
                
                f_id = parts[columMap.get("Index")]   # Modelo
                h1   = parts[columMap.get("h1")]   # 1h
                h10  = parts[columMap.get("h10")]   # 10h
                h100 = parts[columMap.get("h100")]   # 100h
                lh   = parts[columMap.get("lh")]   # FLH
                lw   = parts[columMap.get("lw")]   # FLW
                
                # Valores por defecto para rellenar necesidades
                dynamic = "0"     # 0 para modelos estáticos (estándar)
                sav1    = "2000"  # Superficie/Volumen muerto (valor promedio)
                savlh   = "1500"  # Superficie/Volumen herbáceo vivo
                savlw   = "1500"  # Superficie/Volumen leñoso vivo
                depth   = "1.0"   # Profundidad del lecho de combustible (metros)
                xmext   = "0.25"  # Humedad de extinción (25%)
                heatd   = "18600" # Calor combustibles muertos
                heatl   = "18600" # Calor combustibles vivos
                
                r = f"{f_id};{h1};{h10};{h100};{lh};{lw};{dynamic};{sav1};{savlh};{savlw};{depth};{xmext};{heatd};{heatl}"
                rows.append(r)
                            
        return header + "\n".join(rows)