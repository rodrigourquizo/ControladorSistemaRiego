# cloud_model_training.py

import functions_framework
import os
import logging
import pickle
import pandas as pd
from google.cloud import storage
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.metrics import classification_report

# ID del proyecto de Google Cloud
os.environ["GOOGLE_CLOUD_PROJECT"] = "sistemariegointeligente"

# Configuración del logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

@functions_framework.http
def train_model(request):
    """
    Función en la nube para entrenar el modelo de Machine Learning.
    Lee los datos desde Cloud Storage, entrena el modelo y lo guarda nuevamente en Cloud Storage.
    """
    # Inicializar el cliente de Cloud Storage
    client = storage.Client()
    bucket_name = 'sistema-riego-datos-admin'
    bucket = client.get_bucket(bucket_name)

    try:
        # Obtener la lista de blobs en la carpeta 'decision_data/'
        blobs = bucket.list_blobs(prefix='decision_data/')

        data_frames = []

        for blob in blobs:
            if blob.name.endswith('.csv'):
                # Descargar el contenido del blob
                content = blob.download_as_string().decode('utf-8')
                # Convertir el contenido CSV a DataFrame
                df = pd.read_csv(pd.compat.StringIO(content))
                data_frames.append(df)

        if not data_frames:
            logging.info("No hay datos disponibles para entrenar el modelo.")
            return ('No hay datos para entrenar.', 200)

        # Concatenar todos los DataFrames
        data = pd.concat(data_frames, ignore_index=True)

        # Preprocesamiento de datos
        required_columns = ['humidity', 'temperature', 'ph', 'ce', 'water_level', 'flow_rate',
                            'activar_bomba', 'abrir_valvula_riego', 'inyectar_fertilizante', 'abrir_valvula_suministro']

        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            logging.error(f"Faltan las siguientes columnas en los datos: {missing_columns}")
            return (f"Error: Faltan columnas en los datos: {missing_columns}", 500)

        # Definir las características (X) y la variable objetivo (y)
        X = data[['humidity', 'temperature', 'ph', 'ce', 'water_level', 'flow_rate']]
        # Crear una variable objetivo basada en las acciones tomadas
        # Por ejemplo, si 'activar_bomba' y 'abrir_valvula_riego' son True, el sistema decidió regar
        data['target'] = data.apply(lambda row: int(row['activar_bomba'] and row['abrir_valvula_riego']), axis=1)
        y = data['target']

        # Dividir los datos en conjuntos de entrenamiento y prueba
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

        # Definir el grid de hiperparámetros a probar
        param_grid = {
            'n_estimators': [50, 100, 150],
            'max_depth': [None, 10, 20],
            'min_samples_split': [2, 5, 10]
        }

        # Configurar la búsqueda de los mejores hiperparámetros
        grid_search = GridSearchCV(RandomForestClassifier(), param_grid, cv=3)

        # Entrenar el modelo
        grid_search.fit(X_train, y_train)

        # Obtener el mejor modelo entrenado
        model = grid_search.best_estimator_

        # Evaluación del modelo
        y_pred = model.predict(X_test)
        report = classification_report(y_test, y_pred)
        logging.info(f"Reporte de clasificación:\n{report}")

        # Guardar el modelo entrenado en un archivo temporal
        model_filename = '/tmp/modelo_actualizado.pkl'
        with open(model_filename, 'wb') as model_file:
            pickle.dump(model, model_file)

        # Subir el modelo al bucket en la carpeta 'models/'
        model_blob = bucket.blob('models/modelo_actualizado.pkl')
        model_blob.upload_from_filename(model_filename)

        logging.info("Modelo entrenado y guardado en Cloud Storage.")

        return ('Modelo entrenado y guardado en Cloud Storage.', 200)

    except Exception as e:
        logging.error(f"Error durante el entrenamiento del modelo: {e}")
        return (f"Error durante el entrenamiento: {e}", 500)
