import rasterio
import numpy as np
import pandas as pd
from rasterio.windows import Window
#importante pasar primero el index de plantas y detrás el de modelos
def codificacion_cantor(x,y): 
    x=x.astype(np.int64)
    y=y.astype(np.int64)  
    z=((x+y)*(x+y+1)//2)+y
    z[(x == 0) | (y == 0)] = 0
    return z.astype(np.int32)

def decodificacion_cantor(z):
    w = np.floor((np.sqrt(8*z+1)-1)/2)
    t = (w**2+w)/2
    y = z-t
    x = w-y
    return x,y

#Recibe los path a los archivos
def join_parameters_tif(raster_plants,raster_models, raster_output):
    with rasterio.open(raster_plants) as src_plants, rasterio.open(raster_models) as src_models:
        meta = src_plants.meta.copy()
        meta.update({'dtype': 'int32'})
        nodata_val_plantas = src_plants.nodata
        nodata_val_modelos = src_models.nodata 
        valor_aux= 6
        total_w, total_h = src_plants.width, src_plants.height
        win_w = total_w // valor_aux
        win_h = total_h // valor_aux

        with rasterio.open(raster_output, "w", **meta) as output:

            for i in range(valor_aux):
                for j in range(valor_aux):
                    off_x = i * win_w
                    off_y = j * win_h
                    w = win_w if i < valor_aux - 1 else total_w - off_x
                    h = win_h if j < valor_aux - 1 else total_h - off_y
                    
                    win = Window(off_x, off_y, w, h)
                    data_plants = src_plants.read(1, window=win)
                    data_plants[data_plants == nodata_val_plantas] = 0
                    data_models = src_models.read(1, window=win)
                    data_models[data_models == nodata_val_modelos] = 0

                    data_join = codificacion_cantor(data_plants, data_models)

                    output.write(data_join, 1, window=win)

#Crea el csv combinado con los indices de un index map de la forma (Indice combinado: Indice en el netCDF)
def join_parameters_csv(csv_models, csv_plants, csv_join, index_map=None):
    
    #De no existir index_map crea uno con todos los indices del csv_join como llave y valor
    if index_map is None:
        df_join = pd.read_csv(csv_join)
        index_map = {row["Index"]: row["Index"] for i, row in df_join.iterrows()}

    df_models = pd.read_csv(csv_models).set_index("Index")
    df_plants = pd.read_csv(csv_plants).set_index("Index")
    new_rows = []
    
    for index in index_map:
        index_plant, index_model = decodificacion_cantor(index)
        if index<0:
            continue
        try:
            fila = {"Index": index_map[index]}
            fila.update(df_plants.loc[index_plant].to_dict())
            fila.update(df_models.loc[index_model].to_dict())
            new_rows.append(fila)
        except KeyError:
            continue

    df_nuevo = pd.DataFrame(new_rows)
    df_nuevo.to_csv(csv_join, index=False)

def corregir_csv(input_path, output_path):
    import csv

    def limpiar_valor(texto):
        texto = texto.strip().replace('"', '')
        if ',' in texto:
            texto = texto.replace(',', '.')
        try:
            return float(texto)
        except ValueError:
            return texto

    archivo_entrada = input_path
    archivo_salida = output_path

    with open(archivo_entrada, 'r', encoding='utf-8') as f_in:
        lector = csv.reader(f_in, delimiter=',', quotechar='"')
        
        filas_limpias = []
        for fila in lector:
            nueva_fila = [limpiar_valor(celda) for celda in fila]
            filas_limpias.append(nueva_fila)

    with open(archivo_salida, 'w', newline='', encoding='utf-8') as f_out:
        escritor = csv.writer(f_out, delimiter=',')
        escritor.writerows(filas_limpias)
    
