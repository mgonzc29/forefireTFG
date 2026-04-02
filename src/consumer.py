import json
import requests
from simulator import Simulator
from kombu import Connection, Exchange, Queue
from kombu.mixins import ConsumerMixin
from core.config import settings  # Importamos la misma configuración que la API

# Supongamos que aquí tienes tu lógica de simulación
# from simulator import Simulator

class FireSimulationWorker(ConsumerMixin):
    def __init__(self, connection):
        self.connection = connection

    def get_consumers(self, Consumer, channel):
        # Definimos el Exchange y la Queue exactamente igual que en la API
        exchange = Exchange(settings.RABBIT_EXCHANGE, type="direct")
        queue = Queue(
            settings.RABBIT_QUEUE, 
            exchange, 
            routing_key=settings.RABBIT_ROUTING_KEY
        )
        
        # El worker se queda "escuchando" esta cola
        return [Consumer(queues=[queue], callbacks=[self.on_message], accept=['json'])]

    def on_message(self, body, message):
        """
        Esta función se ejecuta cada vez que llega un mensaje a la cola.
        """
        sim_id = body.get("sim_id")
        model = body.get("model")
        dump_mode = body.get("dump_mode")
        params = body.get("params")
        
        print(f" [!] Recibida simulación {sim_id} (Modelo: {model})")

        try:
            simulator = Simulator(model=model, dump_mode=dump_mode)
            results = simulator.simulate(
                geometry=params.get("geometry"),
                init_date_time=params.get("init_date_time", {}).get("param"),
                end_date_time=params.get("end_date_time", {}).get("param"),
                interval=params.get("interval"),
                meteo_data=params.get("meteo_data"),
                firewalls=params.get("firewalls", []) 
            )

            #Subir los resultados
            

            # --- 3. CALLBACK AL BACKEND PRINCIPAL ---
            # Le avisamos al backend que ya terminamos
            callback_payload = {
                "sim_id": sim_id,
                "status": "completed",
                "result_url": s3_url,
                "api_key": settings.API_KEY.get_secret_value() # Para que el backend confíe en nosotros
            }
            
            response = requests.post(
                str(settings.BACKEND_CALLBACK_URL), 
                json=callback_payload,
                timeout=10
            )
            
            if response.status_code == 200:
                print(f" [OK] Backend notificado para simulación {sim_id}")
            else:
                print(f" [!] Error al notificar al backend: {response.status_code}")

            # --- 4. CONFIRMAR MENSAJE ---
            # Le decimos a RabbitMQ que el mensaje se procesó con éxito y puede borrarlo
            message.ack()

        except Exception as e:
            print(f" [X] Error procesando simulación {sim_id}: {str(e)}")
            # Si falla, podemos rechazar el mensaje. 
            # requeue=False evita bucles infinitos si el error es por datos corruptos.
            message.reject(requeue=False)

if __name__ == "__main__":
    print(f" [*] Conectando a RabbitMQ en {settings.RABBIT_URL}")
    with Connection(settings.RABBIT_URL) as conn:
        try:
            worker = FireSimulationWorker(conn)
            worker.run()
        except KeyboardInterrupt:
            print(" [*] Worker detenido por el usuario")
        except Exception as e:
            print(f" [X] Error en el worker: {str(e)}")