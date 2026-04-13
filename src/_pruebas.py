from simulator import Simulator
from datetime import datetime

import simplekml

import xml.etree.ElementTree as ET
import os

def consolidar_kmls_desde_rutas(lista_rutas, nombre_salida="incendio_completo.kml"):
    # Evitamos prefijos raros como ns0:
    ET.register_namespace('', "http://www.opengis.net/kml/2.2")
    
    # Creamos la base del nuevo KML
    kml_root = ET.Element("{http://www.opengis.net/kml/2.2}kml")
    document = ET.SubElement(kml_root, "{http://www.opengis.net/kml/2.2}Document")
    
    ns = "{http://www.opengis.net/kml/2.2}"

    for i, ruta in enumerate(lista_rutas):
        try:
            # Verificamos si el archivo existe para evitar errores
            if not os.path.exists(ruta):
                print(f"Archivo no encontrado: {ruta}")
                continue
            
            # ¡AQUÍ ESTÁ EL CAMBIO!: Leemos el archivo físico
            tree_parcial = ET.parse(ruta)
            root_parcial = tree_parcial.getroot()
            
            # Buscamos el Placemark dentro del archivo
            placemark = root_parcial.find(f".//{ns}Placemark")
            
            if placemark is not None:
                # Le damos un nombre único a cada capa (momento del incendio)
                name_tag = placemark.find(f"{ns}name")
                if name_tag is None:
                    name_tag = ET.SubElement(placemark, f"{ns}name")
                name_tag.text = f"Perímetro - T{i}"
                
                # Lo añadimos al documento maestro
                document.append(placemark)
                
        except Exception as e:
            print(f"Error procesando {ruta}: {e}")

    # Guardamos el resultado final
    final_tree = ET.ElementTree(kml_root)
    final_tree.write(nombre_salida, encoding="utf-8", xml_declaration=True)
    print(f"\nTerminado: Archivo consolidado en '{nombre_salida}'")

# Llama a la función con tu lista de rutas
# consolidar_kmls_desde_rutas(salida)

simulador= Simulator("BalbiNov2011TMdMl","kml")
#simulador= Simulator("Rothermel","kml")

#simulador.ff.execute(f"include[tmp/run.ff]")

with open('data/meteo.json', 'r', encoding='utf-8') as f:
    meteo = f.read()

geometry=[[[-5.487623,42.671154],[-5.489623,42.671154]],[[-5.480623,42.671154],[-5.483623,42.661154]]]
two_poligons =[
    [
        [-5.487923, 42.672454],
        [-5.487123, 42.671654],
        [-5.486623, 42.671154],
        [-5.487923, 42.669854],
        [-5.489223, 42.671154]
    ],
    [
        [-5.476923, 42.672454],
        [-5.475623, 42.671154],
        [-5.476423, 42.670354],
        [-5.476923, 42.669854],
        [-5.478223, 42.671154]
    ]
]
point=[[[-2.95554,41.88742]]]
poligon = [
    [
        [-5.487923, 42.671454], 
        [-5.487423, 42.671154], 
        [-5.487773, 42.670804], 
        [-5.488073, 42.670854], 
        [-5.488423, 42.671154]
    ]
]

firewallsPoligon=[[[-2.94894,41.86442],[-2.94894,41.99902],[-2.94694,41.99902],[-2.94694,41.86442],[-2.94894,41.86442]]]
firewallsLineAndPoint=[[[-2.94894,41.86442,0],[-2.94894,41.99902,0]],[[-2.96554,41.861742,0]]]
poligon_corcega=[[[8.70000,41.95218,0], [8.70024,41.95182,0], [8.69976,41.95182,0], [8.69984,41.95194,0], [8.69992,41.95206,0]]] 
init_date_time="2026-03-09T08:00:00.000Z"
end_date_time="2026-03-09T10:00:00.000Z"

init_dt = datetime.fromisoformat(init_date_time.replace('Z', '+00:00'))
end_dt = datetime.fromisoformat(end_date_time.replace('Z', '+00:00'))
salida= simulador.prueba_simple(point,init_dt, end_dt, 1800, meteo)
consolidar_kmls_desde_rutas(salida)
#-5.46325,42.78618

os._exit(0) 




        
