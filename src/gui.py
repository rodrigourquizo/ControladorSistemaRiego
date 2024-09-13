import requests

class NodeRedInterface:
    def __init__(self):
        # Supongamos que Node-RED está corriendo en localhost en el puerto 1880
        self.node_red_url = "http://localhost:1880/control"
        print("Interfaz gráfica Node-RED inicializada")

    def enviar_datos_a_nodered(self, sensor_values):
        """Envía los datos de los sensores a la interfaz gráfica de Node-RED."""
        try:
            print("Enviando datos a la interfaz gráfica de Node-RED...")
            headers = {'Content-Type': 'application/json'}
            response = requests.post(self.node_red_url, json=sensor_values, headers=headers)

            if response.status_code == 200:
                print("Datos enviados correctamente a Node-RED.")
            else:
                print(f"Error al enviar datos a Node-RED: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Error al conectar con Node-RED: {e}")

    def recibir_comandos(self):
        """Simula la recepción de comandos desde Node-RED para controlar los actuadores manualmente."""
        print("Recibiendo comandos desde Node-RED...")
        # Aquí podrías implementar la lógica para recibir y procesar comandos manuales
        # Para la simulación, asumimos que siempre se reciben comandos correctos
        comandos = {
            'activar_bomba': True,  # Ejemplo de comando recibido desde la GUI
            'abrir_valvula': False
        }
        return comandos
