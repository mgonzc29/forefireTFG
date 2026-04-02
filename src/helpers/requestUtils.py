import os
import requests 
import io
import re

def downloadFile(url):
    api_key = os.getenv("API_KEY")
    if not api_key:
        print("Error: No se encontró la variable de entorno 'APIKEY'.")
        return
    
    headers = {
    "api-key": api_key
    }

    try: 
        with requests.get(url,headers=headers,stream=True) as r:    
            r.raise_for_status()
            memoria_tif = io.BytesIO(r.content)
            memoria_tif.seek(0)
            return memoria_tif
              
    except requests.exceptions.RequestException as e:
        print(f"Error en la descarga: {e}")
