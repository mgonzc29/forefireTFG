from concurrent.futures import ThreadPoolExecutor
import json
import os
import jwt
import requests
from urllib.parse import urlparse, parse_qs
from kombu import Connection, Exchange, Queue
from kombu.mixins import ConsumerMixin
from ddtrace import tracer
from simulator import Simulator
#from helpers.awsUtils import upload_to_s3  #comentado para pruebas locales
from exceptions import InvalidInputError, MissingParameterError, MissingFileError, SimulationPreProcessingError, UnsupportedZoneError

RABBIT_URL = os.getenv("RABBIT_URL")
RABBIT_EXCHANGE = os.getenv("RABBIT_EXCHANGE")
RABBIT_ROUTING_KEY = os.getenv("RABBIT_ROUTING_KEY")
JWTSECRET= os.getenv("JWTSECRET")

RABBIT_QUEUE = "forefire_simulations_queue"
RABBIT_DLQ_QUEUE = "cola_dlq"
MAX_SIMULACIONES = 1

@tracer.wrap("run_simulation", resource="run_simulation")
def _run_simulation(data):
    model = data.get("model")
    dump_mode = data.get("dump_mode")
    params = data.get("params", {})
    sim = Simulator(model, dump_mode)
    try:
        results = sim.simulate(
            geometry=params.get("geometry"),
            init_date_time=params.get("init_date_time"),
            end_date_time=params.get("end_date_time"),
            interval=params.get("interval"),
            meteo_data=json.dumps(params.get("meteo_data", [])),
            firewalls=params.get("firewalls")
        )
        return "200", results
    except (InvalidInputError, UnsupportedZoneError) as e:
        return "400", f"Bad Request: {str(e)}"
    except (MissingParameterError, MissingFileError, SimulationPreProcessingError) as e:
        return "500", f"Internal Server Error: {str(e)}"
    except Exception as e:
        return "500", f"Unexpected error [{type(e).__name__}]: {str(e)}"

def verificar_callback_token(token_recibido, operacion_esperada):
    try:
        payload = jwt.decode(
            token_recibido, 
            JWTSECRET, 
            algorithms=["HS256"]
        )

        if payload.get('operation') != operacion_esperada:
            return False, "El token es válido pero no para esta operación."

    except jwt.ExpiredSignatureError:
        return False, "El token ha expirado."
    except jwt.InvalidSignatureError:
        return False, "La firma del token no es valida."
    except jwt.DecodeError:
        return False, "El token está mal formado."
    except Exception as e:
        return False, f"Error desconocido con el token: {e}"

class FireSimulationConsumer(ConsumerMixin):
    def __init__(self, connection):
        self.connection = connection
        self.executor = ThreadPoolExecutor(max_workers=MAX_SIMULACIONES)

    def get_consumers(self, Consumer, channel):
        exchange = Exchange(RABBIT_EXCHANGE, type="direct")
        
        dlq_queue = Queue(
            "cola_dlq", 
            exchange, 
            routing_key="cola_dlq",
            durable=True
        )
        dlq_queue(channel).declare()
        

        queue = Queue(
            RABBIT_QUEUE,
            exchange,
            routing_key=RABBIT_ROUTING_KEY,
            queue_arguments={
                'x-dead-letter-exchange': RABBIT_EXCHANGE,
                'x-dead-letter-routing-key': 'cola_dlq'
            }
        )
    
        return [Consumer(
            queues=[queue],
            callbacks=[self.on_message],
            accept=['json'],
            prefetch_count=MAX_SIMULACIONES  
        )]

    @tracer.wrap("consume_message", resource="read_message")
    def on_message(self, body, message):
        sim_id = body.get("sim_id")
        model = body.get("model")
        dump_mode = body.get("dump_mode")
        params = body.get("params")
        callback_url = body.get("callback_url")

        span = tracer.current_span()
        if span:
            span.set_tag("sim_id", sim_id)
            span.set_tag("model", model)

        future = self.executor.submit(_run_simulation, body)

        def on_done(fut):
            try:
                status, payload = fut.result()
                span.set_tag("sim_id", sim_id)
                span.set_tag("status", status)
                
                if status == "200":
                    loaded = True
                    with tracer.trace("carga_resultados_s3", resource="carga_resultados_s3") as span:
                        for i, result in enumerate(payload):
                            file_path = f"simulations/{sim_id}/t_{i}.{dump_mode}"
                            #loaded = loaded and upload_to_s3(result, file_path)     #comentado para pruebas locales          
                        span.set_tag("s3_upload_success", loaded)
                    if loaded:
                        with tracer.trace("callback", resource="callback") as span:
                            parsed_url = urlparse(callback_url)
                            query_params = parse_qs(parsed_url.query)
                            token = query_params.get('token', [None])[0]
                            path_parts = parsed_url.path.strip('/').split('/')
                            op = path_parts[-1] if path_parts else None
                            valid, cb_payload = verificar_callback_token(token, op)
                            
                            if valid:
                                callback_payload = {
                                    "sim_id": sim_id,
                                    "status": "completed"
                                }

                                response = requests.post(
                                    str(callback_url),
                                    json=callback_payload,
                                    timeout=10
                                )
                                message.ack()
                            else:
                                span.set_tag("error", cb_payload)
                                error_payload = {
                                    "status_code": 500,
                                    "error_msg": payload,
                                    "original_body": body
                                    
                                }
                                
                                self.connection.Producer().publish(
                                    error_payload,
                                    exchange=RABBIT_EXCHANGE,
                                    routing_key='cola_dlq',
                                    declare=[Queue("cola_dlq", Exchange(RABBIT_EXCHANGE), routing_key="cola_dlq")]
                                )
                                message.ack()
                    
                    else:
                        #decidir si reencolar o matar o que
                        pass
                elif status in ["400","500"]:
                    span.set_tag("error", payload)
                    error_payload = {
                        "status_code": status,
                        "error_msg": payload,
                        "original_body": body
                        
                    }
                    
                    self.connection.Producer().publish(
                        error_payload,
                        exchange=RABBIT_EXCHANGE,
                        routing_key='cola_dlq',
                        declare=[Queue("cola_dlq", Exchange(RABBIT_EXCHANGE), routing_key="cola_dlq")]
                    )
                    message.ack()

            except Exception as e:
                span.set_tag("error", str(e))
                message.reject(requeue=False)

        future.add_done_callback(on_done) 

    def on_consume_end(self, connection, channel):
        self.executor.shutdown(wait=True)

if __name__ == "__main__":
    with tracer.trace("start_consumer", resource="start_consumer") as span:
        with Connection(RABBIT_URL) as conn:
            try:
                worker = FireSimulationConsumer(conn)
                worker.run()
            except KeyboardInterrupt:
                span.set_tag("error", "Worker detenido por el usuario")
            except Exception as e:
                span.set_tag("error", str(e))