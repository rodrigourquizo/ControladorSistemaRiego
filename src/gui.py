# gui.py

import requests
import logging
import threading
import time

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
        self.node_red_available = False  
        # Iniciar el monitoreo de la interfaz en un hilo separado
        threading.Thread(target=self.monitor_interface, daemon=True).start()

    def actualizar_interfaz(self, sensor_values, control_mode, decision=None):
        """
        Envía los datos de los sensores y el modo de control a Node-RED para su visualización.
        Incluye los valores de humedad, pH, CE, nivel de agua, etc.
        También actualiza el estado de los actuadores y muestra alertas visuales si los valores
        están fuera de los límites.

        :param sensor_values: Diccionario con los valores de los sensores.
        :param control_mode: Modo de control actual ('automatic' o 'manual').
        :param decision: Diccionario con las decisiones tomadas (opcional).
        """
        try:
            data = {
                'sensor_values': sensor_values,
                'control_mode': control_mode,
                'decision': decision
            }
            # Enviar los datos a Node-RED mediante una solicitud POST con timeout
            requests.post(f"{self.node_red_url}/update", json=data, timeout=5)
            logging.info("Interfaz de Node-RED actualizada con los últimos datos.")
        except requests.RequestException as e:
            logging.warning(f"No se pudo actualizar la interfaz de Node-RED.")
            # Continuar operando y proporcionar valores predeterminados si es necesario

    def obtener_modo_control(self, retries=3):
        """
        Obtiene el modo de control actual desde Node-RED.
        El sistema puede estar en modo 'automatic' o 'manual', permitiendo al operador alternar entre
        el control automático y manual de los actuadores.

        :param retries: Número de reintentos en caso de fallo.
        :return: 'automatic' o 'manual'
        """
        for attempt in range(retries):
            try:
                # Realizar una solicitud GET para obtener el modo de control con timeout
                response = requests.get(f"{self.node_red_url}/control_mode", timeout=5)
                if response.status_code == 200:
                    self.control_mode = response.json().get('control_mode', 'automatic')
                    logging.info(f"Modo de control obtenido desde Node-RED: {self.control_mode}")
                    return self.control_mode
                else:
                    logging.warning(f"Respuesta inesperada al obtener el modo de control: {response.status_code}")
            except requests.RequestException as e:
                logging.warning(f"Intento {attempt + 1} fallido al obtener modo de control.")
                time.sleep(1)
        logging.error("No se pudo conectar con Node-RED después de varios intentos. Usando modo de control actual.")
        # Proporcionar un valor predeterminado
        return self.control_mode

    def recibir_comandos(self, retries=3):
        """
        Recibe comandos desde Node-RED para el control manual de los actuadores.
        En el modo manual, se permite al operador activar o desactivar la bomba hidráulica,
        las electroválvulas de riego, fertilizante, y suministro de agua.
        También puede especificar el porcentaje de fertilizante y la cantidad de agua a aplicar.

        :param retries: Número de reintentos en caso de fallo.
        :return: Diccionario con los comandos recibidos.
        """
        for attempt in range(retries):
            try:
                # Realizar una solicitud GET para obtener los comandos manuales con timeout
                response = requests.get(f"{self.node_red_url}/manual_commands", timeout=5)
                if response.status_code == 200:
                    commands = response.json()
                    logging.info(f"Comandos recibidos desde Node-RED: {commands}")
                    return commands
                else:
                    logging.warning(f"Respuesta inesperada al obtener comandos manuales: {response.status_code}")
            except requests.RequestException as e:
                logging.warning(f"Intento {attempt + 1} fallido al recibir comandos.")
                time.sleep(1)
        logging.error("No se pudo obtener comandos desde Node-RED después de varios intentos.")
        # Proporcionar comandos por defecto o vacíos
        return {}

    def mostrar_sugerencias(self, sugerencias, retries=3):
        """
        Envía sugerencias al operador a través de Node-RED.
        Las sugerencias son recomendaciones generadas por el sistema para optimizar el riego
        o fertilización, basadas en el análisis de los datos sensoriales.

        :param sugerencias: Diccionario con las sugerencias generadas por el sistema.
        :param retries: Número de reintentos en caso de fallo.
        """
        for attempt in range(retries):
            try:
                # Enviar las sugerencias mediante una solicitud POST con timeout
                requests.post(f"{self.node_red_url}/suggestions", json=sugerencias, timeout=5)
                logging.info("Sugerencias enviadas a Node-RED.")
                return
            except requests.RequestException as e:
                logging.warning(f"Intento {attempt + 1} fallido al enviar sugerencias.")
                time.sleep(1)
        logging.error("No se pudo enviar sugerencias a Node-RED después de varios intentos.")

    def monitor_interface(self):
        """
        Monitorea el estado de la interfaz de Node-RED, verificando periódicamente su disponibilidad.
        En caso de que Node-RED no esté accesible, registra el problema.
        """
        while True:
            try:
                response = requests.get(f"{self.node_red_url}/health", timeout=5)
                if response.status_code == 200:
                    self.node_red_available = True
                    logging.info("Node-RED está disponible.")
                else:
                    self.node_red_available = False
                    logging.warning("Node-RED no está disponible.")
            except requests.RequestException:
                self.node_red_available = False
                logging.warning("Node-RED no está disponible.")
            time.sleep(60)
