# gui.py

import requests
import logging
import threading

# Configuración del logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


class NodeRedInterface:
    """
    Clase para manejar la comunicación con la interfaz gráfica en Node-RED.
    Permite enviar datos de sensores, recibir comandos de control y actualizar el estado del sistema.
    """

    def __init__(self, node_red_url="http://localhost:1880"):
        """
        Inicializa la interfaz gráfica de Node-RED.
        :param node_red_url: URL base de Node-RED.
        """
        self.node_red_url = node_red_url
        self.control_mode = 'automatic'
        self.lock = threading.Lock()

    def actualizar_interfaz(self, sensor_values, control_mode):
        """
        Envía los datos de los sensores y el modo de control a Node-RED para su visualización.
        Se incluyen los valores de humedad, pH, CE, y nivel de agua en el dashboard.
        También se actualiza el estado de los actuadores y se muestran alertas visuales si los valores
        están fuera de los límites.

        :param sensor_values: Diccionario con los valores de los sensores.
        :param control_mode: Modo de control actual ('automatic' o 'manual').
        """
        try:
            data = {
                'sensor_values': sensor_values,
                'control_mode': control_mode
            }
            # Enviar los datos a Node-RED mediante una solicitud POST
            requests.post(f"{self.node_red_url}/update", json=data)
            logging.info("Interfaz de Node-RED actualizada con los últimos datos.")
        except Exception as e:
            logging.warning(f"No se pudo actualizar la interfaz de Node-RED. Continuando en modo simulación. Detalle: {e}")

    def obtener_modo_control(self):
        """
        Obtiene el modo de control actual desde Node-RED.
        El sistema puede estar en modo 'automatic' o 'manual', permitiendo al operador alternar entre
        el control automático y manual de los actuadores.

        :return: 'automatic' o 'manual'
        """
        try:
            # Realizar una solicitud GET para obtener el modo de control
            response = requests.get(f"{self.node_red_url}/control_mode")
            if response.status_code == 200:
                self.control_mode = response.json().get('control_mode', 'automatic')
                logging.info(f"Modo de control obtenido desde Node-RED: {self.control_mode}")
            else:
                logging.warning(f"No se pudo obtener el modo de control. Usando modo actual: {self.control_mode}")
        except Exception:
            logging.warning("Node-RED no está disponible. Usando modo de control actual.")
        return self.control_mode

    def recibir_comandos(self):
        """
        Recibe comandos desde Node-RED para el control manual de los actuadores.
        En el modo manual, se permite al operador activar o desactivar la bomba hidráulica,
        las electroválvulas de riego, fertilizante, y suministro de agua.

        :return: Diccionario con los comandos recibidos.
        """
        try:
            # Realizar una solicitud GET para obtener los comandos manuales
            response = requests.get(f"{self.node_red_url}/manual_commands")
            if response.status_code == 200:
                commands = response.json()
                logging.info(f"Comandos recibidos desde Node-RED: {commands}")
                return commands
            else:
                logging.warning("No se pudieron obtener los comandos manuales desde Node-RED.")
                return {}
        except Exception as e:
            logging.error(f"Error al recibir comandos desde Node-RED: {e}")
            return {}

    def mostrar_sugerencias(self, sugerencias):
        """
        Envía sugerencias al operador a través de Node-RED.
        Las sugerencias son recomendaciones generadas por el sistema para optimizar el riego
        o fertilización, basadas en el análisis de los datos sensoriales.

        :param sugerencias: Diccionario con las sugerencias generadas por el sistema.
        """
        try:
            # Enviar las sugerencias mediante una solicitud POST
            requests.post(f"{self.node_red_url}/suggestions", json=sugerencias)
            logging.info("Sugerencias enviadas a Node-RED.")
        except Exception as e:
            logging.error(f"Error al enviar sugerencias a Node-RED: {e}")
