import os
import re
from typing import Annotated, List, Optional, Tuple
from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, BeforeValidator, Field
from kombu import Connection, Exchange, Queue

RABBIT_URL = os.getenv("RABBIT_URL")
RABBIT_EXCHANGE = os.getenv("RABBIT_EXCHANGE")
RABBIT_ROUTING_KEY = os.getenv("RABBIT_ROUTING_KEY")

RABBIT_QUEUE = "forefire_simulations_queue"
RABBIT_DLQ_QUEUE = "cola_dlq"

#definimos la forma de las estructuras de datos que nos tienen que llegar
def validate_safety(v):
    if isinstance(v, str):
        dangerous = [r"<script.*?>", r"drop\s+table", r"delete\s+from", r"--", r"<\s*[^>]*>"]
        if any(re.search(p, v.lower()) for p in dangerous):
            raise ValueError("Contenido peligroso detectado")
        return v.strip()
    return v

# 2. EL TIPO "TEXTO SEGURO"
SafeStr = Annotated[str, BeforeValidator(validate_safety)]

# 3. EL TIPO "PUNTO [LAT, LON]"
# Esto valida rango y formato de una vez
SafePoint = Tuple[
    Annotated[float, Field(ge=-90, le=90)], 
    Annotated[float, Field(ge=-180, le=180)]
]

# 4. MODELOS FINALES (Sin clases anidadas innecesarias)
class MeteoVariable(BaseModel):
    ID: SafeStr
    VARIABLE: SafeStr
    VALORES: List[float]

class SimulationParameters(BaseModel):
    sim_id: int = Field(gt=0)
    init_date_time: SafeStr
    end_date_time: SafeStr
    interval: int = Field(gt=0, le=86400)
    geometry: List[List[SafePoint]] 
    meteo_data: List[MeteoVariable]
    firewalls: Optional[List[List[SafePoint]]] = None

app = FastAPI()
exchange = Exchange(RABBIT_EXCHANGE, type="direct")
dlq_queue = Queue(RABBIT_DLQ_QUEUE, exchange, routing_key="cola_dlq")
queue = Queue(
    RABBIT_QUEUE, 
    exchange, 
    routing_key=RABBIT_ROUTING_KEY,
    queue_arguments={
        'x-dead-letter-exchange': RABBIT_EXCHANGE,
        'x-dead-letter-routing-key': RABBIT_DLQ_QUEUE
    }
)


@app.post("/api/v1/simulate/{model}", status_code=status.HTTP_202_ACCEPTED)
def queue_simulation(
    model: SafeStr,  
    dump_mode: SafeStr = Query("geojson", alias="dumpmode"), 
    datos: SimulationParameters = None,
    callback_url: SafeStr = Query("geojson", alias="callbackURL"), 
):

    payload = {
        "model": model,
        "dump_mode": dump_mode,
        "params": datos.model_dump() if datos else {}, 
        "persistence_url": "", 
        "callback_url": callback_url
    }

    try:
        with Connection(RABBIT_URL) as conn:
            producer = conn.Producer(serializer='json')
            producer.publish(
                payload,
                exchange=exchange,
                routing_key=RABBIT_ROUTING_KEY,
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

@app.post("/getModels")
def get_models():
    return 0

@app.post("/getDumpModes")
def get_dump_modes():
    return 0

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "API:app",      
        host="0.0.0.0",  
        port=8000,       
        reload=True,     
        workers=1       
    )