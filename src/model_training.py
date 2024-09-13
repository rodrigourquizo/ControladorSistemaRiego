from sklearn.ensemble import RandomForestClassifier
import pickle

class ModelTraining:
    def __init__(self):
        self.model_path = "modelo_actualizado.pkl"
        self.model = None
        print("Entrenamiento de modelos inicializado")

    def entrenar_modelo_local(self, datos_entrenamiento, decisiones_entrenamiento):
        """Entrena un modelo de Random Forest con datos locales."""
        print("Entrenando modelo local...")
        modelo = RandomForestClassifier(n_estimators=100)
        modelo.fit(datos_entrenamiento, decisiones_entrenamiento)
        
        # Guardar el modelo entrenado localmente
        with open(self.model_path, "wb") as f:
            pickle.dump(modelo, f)
        print("Modelo entrenado localmente y guardado en archivo.")

    def cargar_modelo(self):
        """Carga el modelo entrenado desde un archivo local o la nube."""
        try:
            print("Cargando modelo desde archivo local...")
            with open(self.model_path, "rb") as f:
                self.model = pickle.load(f)
            print("Modelo cargado exitosamente.")
        except FileNotFoundError:
            print("Archivo de modelo no encontrado. Por favor, descarga el modelo desde la nube.")

    def actualizar_modelo(self):
        """Simula la actualización del modelo desde la nube."""
        print("Actualizando modelo de la nube...")
        self.cargar_modelo()  # Simulación de descarga y carga del modelo
        print("Modelo actualizado y listo para su uso.")
