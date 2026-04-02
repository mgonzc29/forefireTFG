import re
from typing import List
from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from kombu import Connection, Exchange, Queue
from pydantic_settings import BaseSettings, SettingsConfigDict

from simulator import Simulator 



#definimos la forma de las estructuras de datos que nos tienen que llegar
class SafetyBaseModel(BaseModel):
    #En este modelo defino decoradores para limpiar determinados tipos de datos
    @field_validator('*', mode='before')
    @classmethod
    def check_malicious_strings(cls, v):
        if isinstance(v, str):
            dangerous_patterns = [
                r"<script.*?>", 
                r"drop\s+table", 
                r"delete\s+from",
                r"truncate\s+table",
                r"insert\s+into",
                r"--", # Comentarios SQL
                r"<\s*[^>]*>" # Cualquier etiqueta HTML
            ]
            
            v_lower = v.lower()
            for pattern in dangerous_patterns:
                if re.search(pattern, v_lower):
                    raise ValueError(f"Contenido potencialmente peligroso detectado en el campo.")
            
            # 2. Opcional: Limpiar espacios en blanco innecesarios
            return v.strip()
        return v

#to do esto creo que da error asi que tengo que quitarlo
class TextParameter(SafetyBaseModel):
    param: str

class MeteoVariable(SafetyBaseModel):
    ID: str
    VARIABLE: str
    VALORES: List[float]

class MeteoData(SafetyBaseModel):
    root: List[MeteoVariable]

class Point(SafetyBaseModel):
    lat: float = Field(ge=-90, le=90, description="Latitud entre -90 y 90")
    lon: float = Field(ge=-180, le=180, description="Longitud entre -180 y 180")

class Geometry(SafetyBaseModel):
    geometry: List[List[Point]]

class SimulationParameters(SafetyBaseModel):
    sim_id: int = Field(gt=0, description="ID de simulación debe ser un entero positivo")
    init_date_time: TextParameter
    end_date_time: TextParameter
    interval: int = Field(gt=0, le=86400, description="Intervalo en segundos")
    geometry: Geometry
    meteo_data: MeteoData


class Settings(BaseSettings):
    RABBIT_URL: str = Field(..., alias="RABBIT_URL")
    RABBIT_EXCHANGE: str
    RABBIT_QUEUE: str
    RABBIT_ROUTING_KEY: str

    S3_ACCESS_KEY: str 
   
    model_config = SettingsConfigDict(
        env_file=".env",           
        env_file_encoding="utf-8", 
        extra="ignore"            
    )

settings = Settings()
app = FastAPI()
exchange = Exchange(settings.RABBIT_EXCHANGE, type="direct")
queue = Queue(settings.RABBIT_QUEUE, exchange, routing_key=settings.RABBIT_ROUTING_KEY)


@app.post("api/v1/simulate/{model}", status_code=status.HTTP_202_ACCEPTED)
def queue_simulation(
    model: TextParameter, 
    dump_mode: TextParameter = Query("geojson", alias="dumpmode"),
    datos: SimulationParameters = None
):
    
    payload = {
        "sim_id": datos.sim_id,
        "model": model,
        "dump_mode": dump_mode,
        "params": datos.dict() 
    }

    try:
        with Connection(settings.RABBIT_URL) as conn:
            producer = conn.Producer(serializer='json')
            producer.publish(
                payload,
                exchange=exchange,
                routing_key=settings.RABBIT_ROUTING_KEY,
                declare=[queue],
                retry=True
            )
        
        return {
            "status": "accepted",
            "sim_id": datos.sim_id,
            "message": f"La simulación {datos.sim_id} ha sido encolada."
        }
    except Exception as e:
        raise HTTPException(
            status_code=503, 
            detail=f"Error al conectar con RabbitMQ: {str(e)}"
        )


@app.post("/loadParameters")
def load_parameters():
    return 0
