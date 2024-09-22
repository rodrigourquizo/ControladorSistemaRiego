# model_training.py

import os
import pickle
import logging
import threading

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.metrics import classification_report

# Configuración del logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


class ModelTraining:
    def __init__(self, model_path="modelo_actualizado.pkl", data_path="data/sensor_data.csv"):
        """
        Inicializa el módulo de entrenamiento de modelos.
        Configura la ruta para guardar o cargar el modelo entrenado y la ruta de los datos.

        :param model_path: Ruta donde se guarda el modelo entrenado.
        :param data_path: Ruta al archivo CSV con los datos de entrenamiento.
        """
        self.model_path = model_path
        self.data_path = data_path
        self.model = None

    def cargar_datos(self):
        """
        Carga los datos desde un archivo CSV.
        Preprocesa los datos y los divide en características (X) y etiquetas (y).

        :return: Tupla (X, y) con los datos preparados.
        """
        try:
            # Cargar los datos desde el CSV
            data = pd.read_csv(self.data_path)
            logging.info("Datos cargados exitosamente para el entrenamiento.")

            # Verificar si la columna 'target' existe
            if 'target' not in data.columns:
                logging.error("La columna 'target' no existe en los datos. No se puede entrenar el modelo.")
                return None, None

            # Seleccionar las características y la etiqueta
            X = data[['humidity', 'ph', 'ce', 'water_level']]
            y = data['target']  # Esta columna debe indicar si se regó o no

            return X, y
        except Exception as e:
            logging.error(f"Error al cargar y preparar los datos: {e}")
            return None, None

    def entrenar_modelo_local(self):
        """
        Entrena un modelo de RandomForest utilizando los datos locales.
        Realiza la validación cruzada y el ajuste de hiperparámetros.
        """
        X, y = self.cargar_datos()
        if X is None or y is None:
            logging.error("No se pudo entrenar el modelo debido a errores en los datos.")
            return

        try:
            # Dividir los datos en conjuntos de entrenamiento y prueba
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
            # Definir el grid de hiperparámetros a probar
            param_grid = {
                'n_estimators': [50, 100],
                'max_depth': [None, 10],
                'min_samples_split': [2, 5]
            }
            # Configurar la búsqueda de los mejores hiperparámetros
            grid_search = GridSearchCV(RandomForestClassifier(), param_grid, cv=3)
            # Entrenar el modelo
            grid_search.fit(X_train, y_train)

            # Obtener el mejor modelo entrenado
            self.model = grid_search.best_estimator_

            # Evaluación del modelo
            y_pred = self.model.predict(X_test)
            report = classification_report(y_test, y_pred)
            logging.info(f"Reporte de clasificación:\n{report}")

            # Guardar el modelo entrenado
            self.guardar_modelo()

        except Exception as e:
            logging.error(f"Error durante el entrenamiento del modelo: {e}")

    def guardar_modelo(self):
        """
        Guarda el modelo entrenado en un archivo local.
        """
        try:
            with open(self.model_path, 'wb') as f:
                pickle.dump(self.model, f)
            logging.info(f"Modelo entrenado guardado en {self.model_path}")
        except Exception as e:
            logging.error(f"Error al guardar el modelo: {e}")

    def cargar_modelo(self):
        """
        Carga el modelo entrenado desde un archivo local.
        """
        try:
            with open(self.model_path, 'rb') as f:
                self.model = pickle.load(f)
            logging.info("Modelo cargado exitosamente.")
        except Exception as e:
            logging.error(f"Error al cargar el modelo: {e}")
            self.model = None

    def predecir(self, X):
        """
        Realiza predicciones utilizando el modelo cargado.

        :param X: Datos de entrada para realizar predicciones (DataFrame o array).
        :return: Predicciones del modelo.
        """
        if self.model is None:
            logging.error("No hay un modelo cargado para realizar predicciones.")
            return None
        try:
            predictions = self.model.predict(X)
            return predictions
        except Exception as e:
            logging.error(f"Error al realizar predicciones: {e}")
            return None

    def entrenar_modelo_en_nube(self):
        """
        Envía datos a la nube para entrenar el modelo con más recursos y datos adicionales.
        Puede incluir datos meteorológicos.
        """
        # Este método puede implementar la lógica para iniciar el entrenamiento en la nube
        # o para subir datos necesarios para el entrenamiento
        logging.info("Funcionalidad para entrenar modelo en la nube no implementada aún.")

    # Métodos adicionales según sea necesario
