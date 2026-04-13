from concurrent.futures import ThreadPoolExecutor
import io
import logging
import threading
import boto3
from botocore.exceptions import ClientError
import os
from dotenv import load_dotenv
from datetime import datetime
from PIL import UnidentifiedImageError
import urllib.error
import pandas as pd
from botocore.config import Config
os.environ["DD_TRACE_ENABLED"] = "false"


#Máximo de hilos concurrentes
cpus = os.cpu_count() or 2
max_workers=cpus * 5

# Carga de variables de entorno desde el archivo .env
load_dotenv()
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION")
AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")

# Inicialización del cliente S3 de AWS
config = Config(
    max_pool_connections=max_workers
)

s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_DEFAULT_REGION,
    config=config
)

# Configuración del sistema de logging
logging.basicConfig(
    filename='miPrograma.log',  # Archivo donde se guardan los logs
    filemode='w',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def upload_to_s3(file_path, s3_object_name):
    try:
        s3.upload_file(file_path, AWS_BUCKET_NAME, s3_object_name)
        logging.info(f"Archivo {file_path} subido exitosamente a {AWS_BUCKET_NAME}/{s3_object_name}")
        return True
    
    except FileNotFoundError:
        logging.error(f"Error: El archivo local no se encontró en {file_path}")
        return False
    except ClientError as e:
        logging.error(f"Error de Boto3: {e}")
        return False
    except Exception as e:
        logging.error(f"Error inesperado: {e}")
        return False