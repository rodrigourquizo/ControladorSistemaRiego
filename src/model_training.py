# model_training.py

import os
import pickle
import logging
import pandas as pd
import numpy as np

from sklearn.model_selection import RandomizedSearchCV, train_test_split
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import MinMaxScaler
from sklearn.ensemble import IsolationForest

from xgboost import XGBRegressor

logger = logging.getLogger('model_training')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

class ModelTraining:
    def __init__(self, model_path="data/modelo_actualizado.pkl", data_path="data/decision_data.csv"):
        """
        Inicializa el módulo de entrenamiento de modelos.
        Configura la ruta para guardar o cargar el modelo entrenado y la ruta de los datos.

        :param model_path: Ruta donde se guarda el modelo entrenado.
        :param data_path: Ruta al archivo CSV con los datos de entrenamiento.
        """
        self.model_path = model_path
        self.data_path = data_path
        self.model = None
        self.scaler = None
        self.features = None

    def cargar_datos(self):
        """
        Carga los datos desde un archivo CSV.
        Preprocesa los datos y los divide en características (X) y etiquetas (y).

        :return: Tupla (X_scaled, y) con los datos preparados.
        """
        try:
            # Cargar los datos desde el CSV
            data = pd.read_csv(self.data_path)
            logging.info("Datos cargados exitosamente para el entrenamiento.")

            # Verificar si las columnas objetivo existen
            required_columns = ['humidity', 'temperature', 'ph', 'ce', 'water_level', 'flow_rate',
                                'porcentaje_fertilizante', 'cantidad_agua', 'season']
            missing_columns = [col for col in required_columns if col not in data.columns]
            if missing_columns:
                logging.error(f"Faltan las siguientes columnas en los datos: {missing_columns}")
                return None, None

            # Eliminar filas con valores faltantes
            data = data.dropna(subset=required_columns)

            # Eliminación de outliers usando IsolationForest
            iso = IsolationForest(contamination=0.05, random_state=42)
            X_outliers = data[['humidity', 'temperature', 'ph', 'ce', 'water_level', 'flow_rate']]
            yhat = iso.fit_predict(X_outliers)
            mask = yhat != -1
            data = data[mask]
            logging.info(f"Datos después de eliminar outliers: {data.shape}")

            # Seleccionar las características y las etiquetas
            X = data[['humidity', 'temperature', 'ph', 'ce', 'water_level', 'flow_rate', 'season']]
            y = data[['porcentaje_fertilizante', 'cantidad_agua']]

            # Convertir la columna 'season' a variables dummy 
            X = pd.get_dummies(X, columns=['season'], drop_first=True)

            # Guardar las características para su uso posterior
            self.features = X.columns.tolist()

            # Escalar las características usando MinMaxScaler
            self.scaler = MinMaxScaler()
            X_scaled = self.scaler.fit_transform(X)

            return X_scaled, y
        except Exception as e:
            logging.error(f"Error al cargar y preparar los datos: {e}")
            return None, None

    def entrenar_modelo_local(self):
        """
        Entrena un modelo de XGBoostRegressor utilizando los datos locales.
        """
        X, y = self.cargar_datos()
        if X is None or y is None:
            logging.error("No se pudo entrenar el modelo debido a errores en los datos.")
            return

        try:
            # Dividir los datos en conjuntos de entrenamiento y prueba
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42)

            # Definir los hiperparámetros a ajustar
            param_dist = {
                'n_estimators': [50, 100, 150],
                'max_depth': [3, 5, 7],
                'learning_rate': [0.01, 0.05, 0.1],
                'subsample': [0.7, 0.8, 0.9],
                'colsample_bytree': [0.7, 0.8, 0.9],
                'reg_alpha': [0, 0.01, 0.1],
                'reg_lambda': [1, 1.5, 2]
            }

            # Configurar búsqueda aleatoria de hiperparámetros
            random_search = RandomizedSearchCV(
                XGBRegressor(random_state=42),
                param_distributions=param_dist,
                n_iter=30,
                cv=3,
                scoring='neg_mean_squared_error',
                n_jobs=-1,
                verbose=1
            )
            random_search.fit(X_train, y_train)

            # Guardar el mejor modelo
            self.model = random_search.best_estimator_
            logging.info(f"Mejores hiperparámetros encontrados:\n{random_search.best_params_}")

            # Realizar predicciones
            y_pred = self.model.predict(X_test)
            mse = mean_squared_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            logging.info(f"Evaluación del modelo - MSE: {mse:.4f}, R2: {r2:.4f}")

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
                pickle.dump({
                    'model': self.model,
                    'scaler': self.scaler,
                    'features': self.features
                }, f)
            logging.info(f"Modelo entrenado guardado en {self.model_path}")
        except Exception as e:
            logging.error(f"Error al guardar el modelo: {e}")

    def cargar_modelo(self):
        """
        Carga el modelo entrenado desde un archivo local.
        """
        try:
            with open(self.model_path, 'rb') as f:
                model_data = pickle.load(f)
                self.model = model_data['model']
                self.scaler = model_data['scaler']
                self.features = model_data['features']
            logging.info("Modelo cargado exitosamente.")
        except Exception as e:
            logging.error(f"Error al cargar el modelo: {e}")
            self.model = None

    def predecir(self, sensor_values):
        """
        Realiza predicciones utilizando el modelo cargado.

        :param sensor_values: Diccionario con los valores de los sensores.
        :return: Diccionario con las predicciones.
        """
        if self.model is None or self.scaler is None or self.features is None:
            logging.error("No hay un modelo cargado para realizar predicciones.")
            return None
        try:
            # Preparar los datos de entrada
            entrada = pd.DataFrame([sensor_values])

            # Convertir 'season' a variables dummy
            if 'season' in entrada.columns:
                entrada = pd.get_dummies(entrada, columns=['season'], drop_first=True)
            else:
                logging.warning("La columna 'season' no está presente en los datos de entrada.")

            # Asegurarse de que las columnas coinciden con las del modelo
            for col in self.features:
                if col not in entrada.columns:
                    entrada[col] = 0  # Agregar columnas faltantes con valor cero
            entrada = entrada[self.features]

            # Escalar las características
            entrada_scaled = self.scaler.transform(entrada)

            # Realizar la predicción
            prediccion = self.model.predict(entrada_scaled)
            resultado = {
                'porcentaje_fertilizante': max(0, prediccion[0]),
                'cantidad_agua': max(0, prediccion[1])
            }
            return resultado
        except Exception as e:
            logging.error(f"Error al realizar predicciones: {e}")
            return None

    def entrenar_modelo_en_nube(self, cloud_sync):
        """
        Inicia el proceso de entrenamiento del modelo en la nube.
        Utiliza el módulo CloudSync para enviar los datos necesarios.

        :param cloud_sync: Instancia de la clase CloudSync para manejar la sincronización.
        """
        try:
            # Enviar datos a la nube para entrenamiento
            datos_enviados = cloud_sync.enviar_datos()
            if datos_enviados:
                # Iniciar el entrenamiento en la nube
                entrenamiento_iniciado = cloud_sync.entrenar_modelo_en_nube()
                if entrenamiento_iniciado:
                    logging.info("Entrenamiento del modelo en la nube iniciado.")
                else:
                    logging.warning("No se pudo iniciar el entrenamiento en la nube.")
            else:
                logging.warning("No se pudieron enviar los datos de entrenamiento a la nube.")
        except Exception as e:
            logging.error(f"Error al enviar datos de entrenamiento a la nube: {e}")

if __name__ == "__main__":
    trainer = ModelTraining()
    trainer.entrenar_modelo_local()
