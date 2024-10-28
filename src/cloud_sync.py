# cloud_sync.py

import pickle
import time
import os
import logging
import json
import requests
import threading
import queue
from datetime import datetime

# Intentamos importar las librerías de Google Cloud Platform (GCP)
try:
    from google.cloud import storage
    from google.oauth2 import service_account
    from google.auth.exceptions import DefaultCredentialsError  # Importar excepciones de autenticación
except ImportError:
    logging.warning("Librerías de GCP no disponibles. Funcionalidades de nube deshabilitadas.")
    storage = None
    service_account = None

# Configuración del logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

class CloudSync:
    """
    Clase para manejar la sincronización de datos y modelos con Google Cloud Platform.
    Incluye métodos para enviar datos, descargar modelos y verificar conexión a GCP.
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
        except DefaultCredentialsError as e:
            logging.error(f"Error de autenticación: {e}")
            self.client = None
            self.bucket = None
        except Exception as e:
            logging.error(f"No se pudo inicializar el cliente de GCP: {e}")
            self.client = None
            self.bucket = None

    def verificar_conexion(self):
        """
        Verifica la conexión con GCP intentando realizar una operación simple en el bucket.
        Retorna True si hay conexión, False en caso contrario.
        """
        if self.bucket is None:
            logging.warning("Bucket de GCP no inicializado.")
            return False
        try:
            # Intentar listar blobs para verificar conectividad
            blobs = list(self.bucket.list_blobs(max_results=1))
            logging.info("Conexión con GCP verificada exitosamente.")
            return True
        except Exception as e:
            logging.error(f"No se pudo conectar con GCP: {e}")
            return False

    def enviar_datos(self):
        """
        Sube los archivos de datos locales a la nube para almacenamiento y análisis.
        """
        if not self.verificar_conexion():
            logging.warning("No hay conexión con GCP. No se pueden enviar datos a la nube.")
            return False

        try:
            # Archivos locales de datos
            local_files = {
                'data/sensor_data.csv': 'sensor_data/sensor_data.csv',
                'data/decision_data.csv': 'decision_data/decision_data.csv'
            }

            for local_path, cloud_path in local_files.items():
                if os.path.exists(local_path):
                    blob = self.bucket.blob(cloud_path)
                    blob.upload_from_filename(local_path)
                    logging.info(f"Archivo '{local_path}' subido a '{cloud_path}' en la nube.")
                else:
                    logging.warning(f"Archivo local no encontrado: {local_path}")

            return True

        except Exception as e:
            logging.error(f"Error al enviar datos a la nube: {e}")
            return False

    def obtener_modelo_actualizado(self):
        """
        Descarga un modelo de Machine Learning actualizado desde la nube.
        El modelo descargado se guarda localmente en el sistema para su uso.

        :return: True si el modelo se descargó correctamente, False de lo contrario.
        """
        if not self.verificar_conexion():
            logging.warning("No hay conexión con GCP. No se puede descargar el modelo actualizado.")
            return False

        try:
            # Especificar la ruta del modelo en el bucket
            blob = self.bucket.blob('models/modelo_actualizado.pkl')
            if blob.exists():
                # Descargar el modelo y guardarlo localmente
                modelo_path = 'data/modelo_actualizado.pkl'
                blob.download_to_filename(modelo_path)
                logging.info("Modelo actualizado descargado desde la nube.")
                return True
            else:
                logging.info("No se encontró un modelo actualizado en la nube.")
                return False
        except Exception as e:
            logging.error(f"No se pudo descargar el modelo desde la nube: {e}")
            return False

    def entrenar_modelo_en_nube(self):
        """
        Inicia el proceso de entrenamiento del modelo en la nube.
        Envía una solicitud para iniciar el entrenamiento remoto en la nube usando una API o función en GCP.
        """
        if not self.verificar_conexion():
            logging.warning("No hay conexión con GCP. No se puede iniciar el entrenamiento en la nube.")
            return False

        try:
            # URL de la función en la nube
            function_url = 'https://us-central1-sistemariegointeligente.cloudfunctions.net/train_model'
            # Enviar una solicitud POST para activar el entrenamiento
            response = requests.post(function_url)
            if response.status_code == 200:
                logging.info("Entrenamiento del modelo en la nube iniciado correctamente.")
                return True
            else:
                logging.error(f"Error al iniciar el entrenamiento en la nube: {response.text}")
                return False
        except Exception as e:
            logging.error(f"Error al enviar solicitud de entrenamiento a la nube: {e}")
            return False

    def sincronizar_con_nube(self):
        """
        Método principal para sincronizar datos y modelos con la nube.
        """
        logging.info("Iniciando sincronización con la nube...")

        # Enviar datos a la nube
        datos_enviados = self.enviar_datos()

        # Obtener modelo actualizado de la nube
        modelo_descargado = self.obtener_modelo_actualizado()

        # Iniciar entrenamiento en la nube si los datos fueron enviados correctamente
        if datos_enviados:
            self.entrenar_modelo_en_nube()

        return datos_enviados and modelo_descargado
