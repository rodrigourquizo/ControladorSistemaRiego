# cloud_model_training.py

import functions_framework
import os
import logging
import pickle
import pandas as pd
from io import StringIO  # Importar StringIO desde io
from google.cloud import storage
from google.auth.exceptions import DefaultCredentialsError  # Importar excepciones de autenticación
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
from datetime import datetime

# ID del proyecto de Google Cloud
os.environ["GOOGLE_CLOUD_PROJECT"] = "sistemariegointeligente"

# Configuración del logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# Definir el número mínimo de muestras necesarias para entrenar
MINIMUM_REQUIRED_SAMPLES = 100  # Ajustar según tus necesidades

@functions_framework.http
def train_model(request):
    """
    Función en la nube para entrenar el modelo de Machine Learning.
    Lee los datos desde Cloud Storage, entrena el modelo y lo guarda nuevamente en Cloud Storage.
    """
    # Inicializar el cliente de Cloud Storage
    try:
        client = storage.Client()
        bucket_name = 'sistema-riego-datos-admin'
        bucket = client.get_bucket(bucket_name)
    except DefaultCredentialsError as e:
        logging.error(f"Error de autenticación: {e}")
        return ('Error de autenticación', 500)
    except Exception as e:
        logging.error(f"Error al inicializar el cliente de Cloud Storage: {e}")
        return (f"Error al inicializar Cloud Storage: {e}", 500)

    try:
        # Obtener la lista de blobs en la carpeta 'decision_data/'
        blobs = bucket.list_blobs(prefix='decision_data/')

        data_frames = []

        for blob in blobs:
            if blob.name.endswith('.csv'):
                # Descargar el contenido del blob
                content = blob.download_as_string().decode('utf-8')
                # Convertir el contenido CSV a DataFrame
                df = pd.read_csv(StringIO(content))  # Usar io.StringIO
                data_frames.append(df)

        if not data_frames:
            logging.info("No hay datos disponibles para entrenar el modelo.")
            return ('No hay datos para entrenar.', 200)

        # Concatenar todos los DataFrames
        data = pd.concat(data_frames, ignore_index=True)

        # Preprocesamiento de datos
        required_columns = ['humidity', 'temperature', 'ph', 'ce', 'water_level', 'flow_rate',
                            'porcentaje_fertilizante', 'cantidad_agua', 'season']

        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            logging.error(f"Faltan las siguientes columnas en los datos: {missing_columns}")
            return (f"Error: Faltan columnas en los datos: {missing_columns}", 500)

        # Manejo de valores faltantes
        data = data.dropna(subset=required_columns)
        if data.empty:
            logging.error("Los datos están vacíos después de eliminar filas con valores faltantes.")
            return ('No hay datos suficientes para entrenar.', 200)

        # Verificar si hay suficientes datos para entrenar
        if len(data) < MINIMUM_REQUIRED_SAMPLES:
            logging.warning("No hay suficientes datos para entrenar el modelo.")
            return ('No hay suficientes datos para entrenar.', 200)

        # Definir las características (X) y las variables objetivo (y)
        X = data[['humidity', 'temperature', 'ph', 'ce', 'water_level', 'flow_rate', 'season']]
        y = data[['porcentaje_fertilizante', 'cantidad_agua']]

        # Convertir 'season' a variables dummy
        X = pd.get_dummies(X, columns=['season'], drop_first=True)

        # Escalado de características
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # Dividir los datos en conjuntos de entrenamiento y prueba
        X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2)

        # Definir el grid de hiperparámetros a probar
        param_grid = {
            'n_estimators': [100, 200, 300],
            'max_depth': [None, 10, 20],
            'min_samples_split': [2, 5, 10]
        }

        # Configurar la búsqueda de los mejores hiperparámetros
        grid_search = GridSearchCV(RandomForestRegressor(random_state=42), param_grid, cv=3, n_jobs=-1)

        # Entrenar el modelo
        grid_search.fit(X_train, y_train)

        # Obtener el mejor modelo entrenado
        model = grid_search.best_estimator_

        # Evaluación del modelo
        y_pred = model.predict(X_test)
        mse = mean_squared_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        logging.info(f"Evaluación del modelo - MSE: {mse:.4f}, R2: {r2:.4f}")

        # Registrar métricas del modelo
        try:
            metrics_filename = '/tmp/model_metrics.txt'
            with open(metrics_filename, 'a') as f:
                f.write(f"{datetime.now()}: MSE={mse:.4f}, R2={r2:.4f}\n")
            # Subir las métricas al bucket
            metrics_blob = bucket.blob('models/model_metrics.txt')
            metrics_blob.upload_from_filename(metrics_filename)
            logging.info("Métricas del modelo guardadas en Cloud Storage.")
        except Exception as e:
            logging.error(f"Error al guardar las métricas del modelo: {e}")

        # Guardar el modelo entrenado en un archivo temporal
        model_filename = '/tmp/modelo_actualizado.pkl'
        with open(model_filename, 'wb') as model_file:
            pickle.dump({
                'model': model,
                'scaler': scaler,
                'features': X.columns.tolist()
            }, model_file)

        # Subir el modelo al bucket en la carpeta 'models/'
        model_blob = bucket.blob('models/modelo_actualizado.pkl')
        model_blob.upload_from_filename(model_filename)

        logging.info("Modelo entrenado y guardado en Cloud Storage.")

        return ('Modelo entrenado y guardado en Cloud Storage.', 200)

    except Exception as e:
        logging.exception("Error durante el entrenamiento del modelo:")
        return (f"Error durante el entrenamiento: {e}", 500)
