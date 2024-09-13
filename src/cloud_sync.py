import json
import requests

class CloudSync:
    def __init__(self):
        """
        Inicializa el módulo de sincronización con la nube.
        Define la URL de la API de sincronización para enviar datos y descargar modelos.
        """
        self.api_url = "https://api.tuservicio.com/sync"  # URL base de la API en la nube
        print("Sincronización con la nube inicializada")

    def enviar_datos(self, sensor_values):
        """
        Envía los datos de los sensores a la nube para almacenamiento y análisis.
        :param sensor_values: Diccionario con los valores de los sensores (humedad, pH, CE, nivel de agua).
        """
        try:
            print("Enviando datos a la nube...")
            headers = {'Content-Type': 'application/json'}  # Especificamos que enviamos datos en formato JSON
            # Hacemos una solicitud POST para enviar los datos a la API
            response = requests.post(self.api_url, data=json.dumps(sensor_values), headers=headers)

            # Verificamos si la solicitud fue exitosa
            if response.status_code == 200:
                print("Datos sincronizados correctamente con la nube.")
            else:
                # Si hay un error en la sincronización, mostramos el código de estado y el mensaje de error
                print(f"Error en la sincronización: {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            # Capturamos cualquier excepción relacionada con la solicitud HTTP
            print(f"Error al conectar con la nube: {e}")

    def descargar_modelo(self):
        """
        Descarga un modelo de Machine Learning actualizado desde la nube.
        El modelo descargado se guarda localmente para su uso en el sistema.
        """
        try:
            print("Descargando modelo actualizado de la nube...")
            # Hacemos una solicitud GET para obtener el modelo desde la API
            response = requests.get(f"{self.api_url}/modelo")

            # Verificamos si la solicitud fue exitosa
            if response.status_code == 200:
                # Guardamos el modelo en un archivo local
                with open("modelo_actualizado.pkl", "wb") as f:
                    f.write(response.content)
                print("Modelo actualizado descargado exitosamente.")
            else:
                # Si hay un error en la descarga, mostramos el código de estado y el mensaje de error
                print(f"Error en la descarga del modelo: {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            # Capturamos cualquier excepción relacionada con la solicitud HTTP
            print(f"Error al conectar con la nube: {e}")

