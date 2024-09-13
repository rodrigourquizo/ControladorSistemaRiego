from sklearn.ensemble import RandomForestClassifier
import numpy as np
import pandas as pd

class DecisionEngine:
    def __init__(self):
        print("Motor de Toma de Decisiones inicializado")
        # Cargamos el modelo de Random Forest. En este ejemplo, lo inicializamos vacío.
        # En una aplicación real, entrenarías este modelo con datos históricos.
        self.model = RandomForestClassifier(n_estimators=100)
        self._entrenar_modelo_inicial()

    def _entrenar_modelo_inicial(self):
        """Entrena un modelo ficticio de Random Forest con datos generados."""
        # Datos ficticios para entrenar el modelo inicialmente (esto es un ejemplo)
        # Columna 1: Humedad, Columna 2: pH, Columna 3: CE, Columna 4: Nivel de agua
        datos_entrenamiento = np.array([
            [40, 6.5, 2.0, 80],  # Ejemplo de datos históricos
            [60, 6.0, 1.5, 90],
            [55, 7.0, 2.2, 50],
            [30, 6.3, 1.8, 60]
        ])
        # Decisiones: 1 - Activar riego, 0 - No activar
        decisiones_entrenamiento = np.array([1, 0, 0, 1])

        # Entrenamos el modelo
        self.model.fit(datos_entrenamiento, decisiones_entrenamiento)
        print("Modelo de Random Forest entrenado con datos iniciales.")

    def tomar_decision(self, sensor_values):
        """Toma una decisión basada en los valores de los sensores."""
        # Convertimos los valores de los sensores en una fila de entrada para el modelo
        entrada = np.array([[sensor_values['humidity'], sensor_values['ph'],
                             sensor_values['ce'], sensor_values['water_level']]])

        # El modelo predice si se debe activar el riego (1) o no (0)
        decision_riego = self.model.predict(entrada)[0]

        # Generamos una decisión basada en los resultados del modelo
        decision = {
            'activar_riego': decision_riego == 1,
            'activar_bomba': sensor_values['water_level'] > 20,  # Condición ficticia
            'abrir_valvula': decision_riego == 1,
            'inyeccion_fertilizante': sensor_values['ce'] < 1.5  # Ejemplo de decisión de fertilización
        }

        return decision
