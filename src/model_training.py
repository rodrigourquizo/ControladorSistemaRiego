from sklearn.ensemble import RandomForestClassifier
import pickle

class ModelTraining:
    def __init__(self):
        """
        Inicializa el módulo de entrenamiento de modelos, que será responsable de 
        entrenar, guardar, cargar y actualizar el modelo de Machine Learning (Random Forest).
        """
        self.model_path = "modelo_actualizado.pkl"  # Ruta del archivo donde se guardará el modelo entrenado
        self.model = None  # El modelo se inicializa como None hasta que sea cargado o entrenado
        print("Entrenamiento de modelos inicializado")

    def entrenar_modelo_local(self, datos_entrenamiento, decisiones_entrenamiento):
        """
        Entrena un modelo de Random Forest utilizando datos locales proporcionados.
        :param datos_entrenamiento: Matriz de características con datos de sensores (humedad, pH, CE, etc.).
        :param decisiones_entrenamiento: Vector con las decisiones asociadas (1 - Riego, 0 - No Riego).
        """
        print("Entrenando modelo local...")

        # Inicializamos el modelo Random Forest con 100 árboles de decisión
        modelo = RandomForestClassifier(n_estimators=100)

        # Entrenamos el modelo con los datos proporcionados
        modelo.fit(datos_entrenamiento, decisiones_entrenamiento)

        # Guardamos el modelo entrenado localmente en un archivo
        with open(self.model_path, "wb") as f:
            pickle.dump(modelo, f)
        print(f"Modelo entrenado localmente y guardado en {self.model_path}.")

    def cargar_modelo(self):
        """
        Carga el modelo entrenado desde un archivo local. Si el archivo no existe, 
        notifica al usuario que debe descargarse desde la nube.
        """
        try:
            print("Cargando modelo desde archivo local...")
            # Intentamos cargar el modelo desde el archivo especificado
            with open(self.model_path, "rb") as f:
                self.model = pickle.load(f)
            print("Modelo cargado exitosamente.")
        except FileNotFoundError:
            # Si el archivo no se encuentra, notificamos que debe ser descargado
            print(f"Archivo de modelo no encontrado en {self.model_path}. Por favor, descarga el modelo desde la nube.")
        except Exception as e:
            # Capturamos cualquier otra excepción no anticipada
            print(f"Error al cargar el modelo: {e}")

    def actualizar_modelo(self):
        """
        Simula la actualización del modelo desde la nube. En una implementación real, 
        se descargaría el modelo actualizado desde un servicio de almacenamiento en la nube.
        """
        print("Actualizando modelo desde la nube...")

        # En una implementación real, aquí se descargaría el modelo de la nube
        # Simulamos la actualización cargando el modelo local
        self.cargar_modelo()

        # Si el modelo fue cargado correctamente, notificamos que está listo
        if self.model is not None:
            print("Modelo actualizado y listo para su uso.")
        else:
            print("No se pudo actualizar el modelo. Verifica la conexión o la disponibilidad del archivo.")
