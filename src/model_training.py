# model_training.py

import os
import pickle
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.model_selection import RandomizedSearchCV, train_test_split, KFold, cross_val_score
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
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
            X = pd.get_dummies(X, columns=['season'], drop_first=False)

            # Guardar las características para su uso posterior
            self.features = X.columns.tolist()

            # Escalar las características usando MinMaxScaler
            self.scaler = MinMaxScaler()
            X_scaled = self.scaler.fit_transform(X)

            # Realizar EDA
            self.realizar_eda(data, X, y)

            return X_scaled, y
        except Exception as e:
            logging.error(f"Error al cargar y preparar los datos: {e}")
            return None, None

    def realizar_eda(self, data, X, y):
        """
        Realiza un análisis exploratorio de datos sobre las variables objetivo y las características.
        """
        # Combinar X y y para análisis conjunto
        data_eda = pd.concat([X.reset_index(drop=True), y.reset_index(drop=True)], axis=1)

        # Matriz de correlación entre sensores y variables objetivo
        plt.figure(figsize=(12, 10))
        corr_matrix = data_eda.corr()
        sns.heatmap(corr_matrix, annot=True, fmt=".2f", cmap='coolwarm')
        plt.title('Matriz de Correlación entre Sensores y Variables Objetivo')
        plt.tight_layout()
        plt.show()

        # Gráficos de dispersión entre sensores y variables objetivo
        sensor_columns = ['humidity', 'temperature', 'ph', 'ce', 'water_level', 'flow_rate']
        target_columns = ['porcentaje_fertilizante', 'cantidad_agua']

        for target in target_columns:
            plt.figure(figsize=(15, 10))
            for i, sensor in enumerate(sensor_columns):
                plt.subplot(2, 3, i+1)
                sns.scatterplot(data=data_eda, x=sensor, y=target)
                plt.title(f'{sensor} vs {target}')
            plt.tight_layout()
            plt.show()

    def entrenar_modelo_local(self):
        """
        Entrena un modelo de XGBRegressor utilizando los datos locales.
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
                XGBRegressor(random_state=42, objective='reg:squarederror'),
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

            # Validación cruzada
            kf = KFold(n_splits=5, shuffle=True, random_state=42)
            scores = cross_val_score(
                self.model,
                X, y, cv=kf, scoring='neg_mean_squared_error'
            )
            logging.info(f"MSE promedio en validación cruzada: {-np.mean(scores):.4f}")

            # Realizar predicciones
            y_pred = self.model.predict(X_test)
            mse = mean_squared_error(y_test, y_pred)
            mae = mean_absolute_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            logging.info(f"Evaluación del modelo - MSE: {mse:.4f}, MAE: {mae:.4f}, R2: {r2:.4f}")

            # Visualización de las predicciones vs valores reales
            self.visualizar_resultados(y_test, y_pred)

            # Guardar el modelo entrenado
            self.guardar_modelo()

        except Exception as e:
            logging.error(f"Error durante el entrenamiento del modelo: {e}")

    def visualizar_resultados(self, y_test, y_pred):
        """
        Visualiza los resultados de las predicciones del modelo.
        """
        # Convertir y_pred a DataFrame si es necesario
        if isinstance(y_pred, np.ndarray):
            y_pred = pd.DataFrame(y_pred, columns=['porcentaje_fertilizante', 'cantidad_agua'])

        # Para porcentaje de fertilizante
        plt.figure(figsize=(12, 5))

        plt.subplot(1, 2, 1)
        plt.scatter(y_test['porcentaje_fertilizante'], y_pred['porcentaje_fertilizante'], color='blue')
        plt.xlabel('Valor Real')
        plt.ylabel('Predicción')
        plt.title('Porcentaje de Fertilizante: Valor Real vs Predicción')
        plt.plot([y_test['porcentaje_fertilizante'].min(), y_test['porcentaje_fertilizante'].max()],
                 [y_test['porcentaje_fertilizante'].min(), y_test['porcentaje_fertilizante'].max()], 'r--')

        # Para cantidad de agua
        plt.subplot(1, 2, 2)
        plt.scatter(y_test['cantidad_agua'], y_pred['cantidad_agua'], color='green')
        plt.xlabel('Valor Real')
        plt.ylabel('Predicción')
        plt.title('Cantidad de Agua: Valor Real vs Predicción')
        plt.plot([y_test['cantidad_agua'].min(), y_test['cantidad_agua'].max()],
                 [y_test['cantidad_agua'].min(), y_test['cantidad_agua'].max()], 'r--')

        plt.tight_layout()
        plt.show()

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
                entrada = pd.get_dummies(entrada, columns=['season'], drop_first=False)
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
                'porcentaje_fertilizante': max(0, prediccion[0][0]),
                'cantidad_agua': max(0, prediccion[0][1])
            }
            return resultado
        except Exception as e:
            logging.error(f"Error al realizar predicciones: {e}")
            return None

if __name__ == "__main__":
    trainer = ModelTraining()
    trainer.entrenar_modelo_local()
