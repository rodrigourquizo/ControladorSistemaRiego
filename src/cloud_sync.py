# cloud_sync.py

import pickle
import time
import os
import logging
import json
import requests

# Intentamos importar las librerías de Google Cloud Platform (GCP)
try:
    from google.cloud import storage
    from google.oauth2 import service_account
except ImportError:
    logging.warning("Librerías de GCP no disponibles. Funcionalidades de nube deshabilitadas.")
    storage = None
    service_account = None

# Configuración del logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


class CloudSync:
    """
    Clase para manejar la sincronización de datos y modelos con Google Cloud Platform.
    Incluye métodos para enviar datos, descargar modelos y verificar conexión a Internet.
    """

    def __init__(self, credentials_path='config/credentials.json', bucket_name='sistema-riego-datos-admin'):
        """
        Inicializa el módulo de sincronización con la nube.
        Configura las credenciales de Google Cloud Platform y establece conexión con el bucket de GCP.

        :param credentials_path: Ruta al archivo de credenciales de GCP.
        :param bucket_name: Nombre del bucket de Google Cloud Storage.
        """
        self.credentials_path = credentials_path
        self.bucket_name = bucket_name
        self.client = None
        self.bucket = None

        # Inicializar el cliente de GCP si las librerías están disponibles
        if storage and service_account:
            self._initialize_gcp_client()
        else:
            logging.warning("Sincronización con la nube deshabilitada.")

    def _initialize_gcp_client(self):
        """
        Inicializa el cliente de Google Cloud Storage.
        Carga las credenciales y configura la conexión al bucket de GCP.
        """
        try:
            if os.path.exists(self.credentials_path):
                # Cargar las credenciales desde el archivo JSON
                credentials = service_account.Credentials.from_service_account_file(self.credentials_path)
                # Crear un cliente de almacenamiento
                self.client = storage.Client(credentials=credentials)
                # Obtener el bucket especificado
                self.bucket = self.client.get_bucket(self.bucket_name)
                logging.info(f"Conectado al bucket de GCP: {self.bucket_name}")
            else:
                logging.warning(f"Archivo de credenciales no encontrado en {self.credentials_path}. Continuando sin sincronización en la nube.")
                self.client = None
                self.bucket = None
        except Exception as e:
            logging.warning(f"No se pudo inicializar el cliente de GCP. Continuando sin sincronización en la nube. Detalle: {e}")
            self.client = None
            self.bucket = None

    def verificar_conexion(self):
        """
        Verifica la conexión a Internet intentando acceder a un sitio conocido (Google).
        Retorna True si hay conexión, False en caso contrario.
        """
        try:
            requests.get('https://www.google.com', timeout=5)
            return True
        except (requests.ConnectionError, requests.Timeout):
            return False

    def enviar_datos(self, sensor_values):
        """
        Envía los datos de los sensores a la nube para almacenamiento y análisis.
        Genera un archivo JSON con los valores y lo sube al bucket de GCP.

        :param sensor_values: Diccionario con los valores de los sensores (humedad, pH, CE, nivel de agua).
        """
        if not self.verificar_conexion():
            logging.warning("No hay conexión a Internet. No se pueden enviar datos a la nube.")
            return

        if self.bucket is None:
            logging.warning("Sin conexión al bucket de GCP. Datos no enviados.")
            return

        try:
            # Generar nombre de archivo único usando timestamp
            timestamp = sensor_values.get('timestamp', int(time.time()))
            filename = f"sensor_data_{timestamp}.json"

            # Crear un blob en el bucket de GCP
            blob = self.bucket.blob(f"sensor_data/{filename}")
            # Subir los datos como un string JSON
            blob.upload_from_string(
                data=json.dumps(sensor_values),
                content_type='application/json'
            )
            logging.info(f"Datos de sensores enviados a la nube: {filename}")
        except Exception as e:
            logging.warning(f"No se pudieron enviar datos a la nube. Detalle: {e}")

    def obtener_modelo_actualizado(self):
        """
        Descarga un modelo de Machine Learning actualizado desde la nube.
        El modelo descargado se guarda localmente en el sistema para su uso.

        :return: Modelo actualizado si se descargó correctamente, None de lo contrario.
        """
        if not self.verificar_conexion():
            logging.warning("No hay conexión a Internet. No se puede descargar el modelo actualizado.")
            return None

        if self.bucket is None:
            logging.warning("Sin conexión al bucket de GCP. Modelo no descargado.")
            return None

        try:
            # Especificar la ruta del modelo en el bucket
            blob = self.bucket.blob('models/modelo_actualizado.pkl')
            if blob.exists():
                # Descargar el modelo y guardarlo localmente
                modelo_path = 'modelo_actualizado.pkl'
                blob.download_to_filename(modelo_path)
                logging.info("Modelo actualizado descargado desde la nube.")
                # Cargar el modelo descargado
                with open(modelo_path, 'rb') as f:
                    modelo_nuevo = pickle.load(f)
                return modelo_nuevo
            else:
                logging.info("No se encontró un modelo actualizado en la nube.")
                return None
        except Exception as e:
            logging.warning(f"No se pudo descargar el modelo desde la nube. Detalle: {e}")
            return None

    def entrenar_modelo_en_nube(self):
        """
        Inicia el proceso de entrenamiento del modelo en la nube.
        Enviar una solicitud para iniciar el entrenamiento remoto en la nube usando una API o función en GCP.
        """
        if not self.verificar_conexion():
            logging.warning("No hay conexión a Internet. No se puede iniciar el entrenamiento en la nube.")
            return

        try:
            # URL de tu función en la nube
            function_url = 'https://us-central1-sistemariegointeligente.cloudfunctions.net/train_model'
            # Enviar una solicitud POST para activar el entrenamiento
            response = requests.post(function_url)
            if response.status_code == 200:
                logging.info("Entrenamiento del modelo en la nube iniciado correctamente.")
            else:
                logging.error(f"Error al iniciar el entrenamiento en la nube: {response.text}")
        except Exception as e:
            logging.error(f"Error al enviar solicitud de entrenamiento a la nube: {e}")
