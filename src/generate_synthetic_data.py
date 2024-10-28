# generate_synthetic_data.py

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import logging

# Configuración del logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def generate_synthetic_data(num_samples=4320):
    """
    Genera datos sintéticos realistas para entrenar el modelo de Machine Learning.
    Genera datos para 90 días, tomando una muestra cada 30 minutos.

    :param num_samples: Número de muestras a generar (90 días * 24 horas * 2 muestras por hora). 
    """
    data = []

    # Fecha inicial (hace 90 días) 
    start_date = datetime.now() - timedelta(days=90) 
    timestamp = start_date

    # Variables para mantener coherencia temporal
    last_humidity = np.random.uniform(30, 70)
    last_temperature = np.random.uniform(15, 25)
    last_water_level = np.random.uniform(50, 100)
    last_ce = np.random.uniform(1.0, 2.5)
    last_ph = np.random.uniform(5.5, 7.5)
    last_flow_rate = 0.0

    for _ in range(num_samples):
        # Incrementar el timestamp
        timestamp += timedelta(minutes=30)

        # Determinar la estación del año basada en la fecha
        month = timestamp.month
        if month in [12, 1, 2]:
            season = 'summer'
            temp_base = 30
            temp_variation = 5
        elif month in [3, 4, 5]:
            season = 'autumn'
            temp_base = 20
            temp_variation = 5
        elif month in [6, 7, 8]:
            season = 'winter'
            temp_base = 10
            temp_variation = 5
        else:
            season = 'spring'
            temp_base = 20
            temp_variation = 5

        # Generar temperatura con pequeñas variaciones
        temperature = temp_base + np.random.normal(0, temp_variation)
        temperature = np.clip(temperature, 5, 40)
        last_temperature = temperature

        # Generar humedad relativa del aire inversamente proporcional a la temperatura
        humidity_air = 100 - temperature + np.random.normal(0, 5)
        humidity_air = np.clip(humidity_air, 20, 80)

        # Generar humedad del suelo, que aumenta si hubo riego
        if last_flow_rate > 0:
            # Simular aumento de humedad del suelo después de riego
            humidity = last_humidity + np.random.uniform(5, 15)
        else:
            # Disminución natural de la humedad del suelo
            humidity = last_humidity - np.random.uniform(0, 2)
        humidity = np.clip(humidity, 10, 90)
        last_humidity = humidity

        # Generar pH con pequeñas variaciones alrededor de un valor central
        ph = last_ph + np.random.normal(0, 0.05)
        ph = np.clip(ph, 5.0, 8.0)
        last_ph = ph

        # Generar CE con pequeñas variaciones, aumenta ligeramente si se inyectó fertilizante
        ce = last_ce + (0.1 if np.random.rand() < 0.3 else 0) + np.random.normal(0, 0.05)
        ce = np.clip(ce, 0.5, 3.0)
        last_ce = ce

        # Generar nivel de agua del tanque
        if last_flow_rate > 0:
            # Disminuir nivel de agua si hubo riego
            water_level = last_water_level - np.random.uniform(1, 3)
        else:
            # Recuperación lenta del nivel (por ejemplo, por suministro alternativo)
            water_level = last_water_level + (2 if np.random.rand() < 0.1 else 0)
        water_level = np.clip(water_level, 0, 100)
        last_water_level = water_level

        # Decisiones basadas en reglas
        activar_bomba = False
        abrir_valvula_riego = False
        inyectar_fertilizante = False
        abrir_valvula_suministro = False
        porcentaje_fertilizante = 0.0
        cantidad_agua = 0.0
        flow_rate = 0.0

        # Lógica de riego
        if humidity < 40 or temperature > 30:
            activar_bomba = True
            abrir_valvula_riego = True
            cantidad_agua = np.random.uniform(10, 30)
            flow_rate = np.random.uniform(20, 60)
        else:
            flow_rate = 0.0

        # Lógica de fertilización
        if ce < 1.0:
            inyectar_fertilizante = True
            porcentaje_fertilizante = np.random.uniform(1, 5)

        # Lógica de suministro alternativo
        if water_level < 20:
            abrir_valvula_suministro = True
            water_level += np.random.uniform(10, 30)  # Simular llenado del tanque
            water_level = np.clip(water_level, 0, 100)

        # Actualizar last_flow_rate
        last_flow_rate = flow_rate

        # Crear el registro de datos
        sample = {
            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'humidity': round(humidity, 1),
            'temperature': round(temperature, 1),
            'ph': round(ph, 2),
            'ce': round(ce, 2),
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
