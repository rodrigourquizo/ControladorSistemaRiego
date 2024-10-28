# generate_synthetic_data.py

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import logging

# Configuración del logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def generate_synthetic_data(num_samples=1000):
    """
    Genera datos sintéticos realistas para entrenar el modelo de Machine Learning.

    :param num_samples: Número de muestras a generar.
    """
    data = []

    # Fecha inicial
    start_date = datetime.now() - timedelta(days=30)
    timestamp = start_date

    # Variables para mantener coherencia temporal
    last_humidity = np.random.uniform(30, 70)
    last_temperature = np.random.uniform(15, 35)
    last_water_level = np.random.uniform(50, 100)
    last_ce = np.random.uniform(1.0, 2.5)
    last_ph = np.random.uniform(5.5, 7.5)

    for _ in range(num_samples):
        # Incrementar el timestamp
        timestamp += timedelta(minutes=30)

        # Generar temperatura con pequeñas variaciones
        temperature = last_temperature + np.random.normal(0, 1)
        temperature = np.clip(temperature, 5, 40)
        last_temperature = temperature

        # Generar humedad inversamente proporcional a la temperatura
        humidity = 100 - temperature + np.random.normal(0, 5)
        humidity = np.clip(humidity, 20, 80)
        last_humidity = humidity

        # Generar pH con pequeñas variaciones alrededor de un valor central
        ph = last_ph + np.random.normal(0, 0.1)
        ph = np.clip(ph, 5.0, 8.0)
        last_ph = ph

        # Generar CE con pequeñas variaciones
        ce = last_ce + np.random.normal(0, 0.1)
        ce = np.clip(ce, 0.5, 3.0)
        last_ce = ce

        # Generar nivel de agua con tendencia a disminuir si no se rellena
        water_level = last_water_level - np.random.uniform(0, 1)
        if water_level < 20:
            water_level = 100  # Simular relleno del tanque
        last_water_level = water_level

        # Generar flow_rate basado en la actividad del riego
        flow_rate = np.random.uniform(0, 60) if humidity < 50 else np.random.uniform(0, 10)

        # Determinar la estación del año basada en la fecha
        month = timestamp.month
        if month in [12, 1, 2]:
            season = 'summer'
        elif month in [3, 4, 5]:
            season = 'autumn'
        elif month in [6, 7, 8]:
            season = 'winter'
        else:
            season = 'spring'

        # Decisiones basadas en umbrales
        activar_bomba = humidity < 50
        abrir_valvula_riego = activar_bomba
        inyectar_fertilizante = ce < 1.5
        abrir_valvula_suministro = water_level < 30

        # Porcentaje de fertilizante y cantidad de agua
        porcentaje_fertilizante = np.random.uniform(0, 5) if inyectar_fertilizante else 0
        cantidad_agua = np.random.uniform(10, 50) if activar_bomba else 0

        # Crear el registro de datos
        sample = {
            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'humidity': round(humidity,1),
            'temperature': round(temperature, 1),
            'ph': round(ph, 1),
            'ce': round(ce, 1),
            'water_level': round(water_level, 1),
            'flow_rate': round(flow_rate, 1),
            'season': season,
            'activar_bomba': activar_bomba,
            'abrir_valvula_riego': abrir_valvula_riego,
            'inyectar_fertilizante': inyectar_fertilizante,
            'abrir_valvula_suministro': abrir_valvula_suministro,
            'porcentaje_fertilizante': round(porcentaje_fertilizante, 1),
            'cantidad_agua': round(cantidad_agua, 1)
        }

        data.append(sample)

    df = pd.DataFrame(data)

    # Crear el directorio 'data' si no existe
    os.makedirs('data', exist_ok=True)

    # Guardar en CSV
    df.to_csv('data/decision_data.csv', index=False)
    logging.info("Datos sintéticos generados y guardados en 'data/decision_data.csv'.")

if __name__ == "__main__":
    generate_synthetic_data()
