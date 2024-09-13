import requests

class NodeRedInterface:
    def __init__(self):
        """
        Inicializa la interfaz gráfica de Node-RED.
        Node-RED está corriendo en el puerto 1880 de localhost, y esta clase se encarga de 
        la comunicación con esa interfaz para enviar y recibir datos.
        """
        self.node_red_url = "http://localhost:1880/control"  # URL de Node-RED en el puerto 1880
        print("Interfaz gráfica Node-RED inicializada")

    def enviar_datos_a_nodered(self, sensor_values):
        """
        Envía los datos de los sensores a la interfaz gráfica de Node-RED para su visualización.
        :param sensor_values: Diccionario con los valores de los sensores (humedad, pH, CE, nivel de agua).
        """
        try:
            print("Enviando datos a la interfaz gráfica de Node-RED...")
            headers = {'Content-Type': 'application/json'}  # Se envían los datos como JSON
            # Realizamos una solicitud POST para enviar los datos a Node-RED
            response = requests.post(self.node_red_url, json=sensor_values, headers=headers)

            # Verificamos si la solicitud fue exitosa
            if response.status_code == 200:
                print("Datos enviados correctamente a Node-RED.")
            else:
                # Si hay un error en el envío, mostramos el código de estado y el mensaje de error
                print(f"Error al enviar datos a Node-RED: {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            # Capturamos cualquier excepción relacionada con la solicitud HTTP
            print(f"Error al conectar con Node-RED: {e}")

    def recibir_comandos(self):
        """
        Simula la recepción de comandos desde la interfaz gráfica de Node-RED.
        Estos comandos podrían ser usados para controlar manualmente los actuadores (bomba, válvulas).
        :return: Diccionario con los comandos recibidos desde Node-RED.
        """
        print("Recibiendo comandos desde Node-RED...")
        # Aquí podrías implementar la lógica real para recibir comandos desde Node-RED
        # Para esta simulación, asumimos que los comandos siempre se reciben correctamente.
        # Ejemplo de comandos:
        comandos = {
            'activar_bomba': True,   # Comando para activar la bomba recibido desde la GUI
            'abrir_valvula': False   # Comando para cerrar la válvula
        }
        return comandos
