from sklearn.ensemble import RandomForestClassifier
import numpy as np
import pandas as pd

class DecisionEngine:
    def __init__(self):
        """
        Inicializa el motor de toma de decisiones con un modelo de Random Forest.
        El modelo se entrena inicialmente con datos ficticios para simular decisiones.
        """
        print("Motor de Toma de Decisiones inicializado")

        # Inicialización del modelo Random Forest con 100 árboles de decisión
        self.model = RandomForestClassifier(n_estimators=100)

        # Entrenar el modelo con datos ficticios para simular su funcionamiento
        self._entrenar_modelo_inicial()

    def _entrenar_modelo_inicial(self):
        """
        Entrena un modelo ficticio de Random Forest con datos simulados.
        En una implementación real, se entrenaría con datos históricos de sensores.
        """
        # Datos ficticios: Humedad, pH, CE y Nivel de agua
        datos_entrenamiento = np.array([
            [40, 6.5, 2.0, 80],  # Ejemplo de datos históricos de sensores
            [60, 6.0, 1.5, 90],
            [55, 7.0, 2.2, 50],
            [30, 6.3, 1.8, 60]
        ])

        # Decisiones asociadas (1 - Activar riego, 0 - No activar riego)
        decisiones_entrenamiento = np.array([1, 0, 0, 1])

        # Entrenamos el modelo Random Forest con los datos simulados
        self.model.fit(datos_entrenamiento, decisiones_entrenamiento)
        print("Modelo de Random Forest entrenado con datos iniciales.")

    def tomar_decision(self, sensor_values):
        """
        Toma una decisión basada en los valores de los sensores actuales.
        :param sensor_values: diccionario con los valores de los sensores (humedad, pH, CE, nivel de agua).
        :return: diccionario con las decisiones de activación de riego, bomba, válvulas y fertilización.
        """
        print("Procesando decisión basada en los valores de sensores...")

        # Convertimos los valores de los sensores en una fila de entrada para el modelo
        entrada = np.array([[sensor_values['humidity'], sensor_values['ph'],
                             sensor_values['ce'], sensor_values['water_level']]])

        # El modelo predice si se debe activar el riego (1) o no (0)
        decision_riego = self.model.predict(entrada)[0]

        # Generamos una decisión basada en los resultados del modelo y reglas adicionales
        decision = {
            'activar_riego': decision_riego == 1,  # Activar riego si la predicción es 1
            'activar_bomba': sensor_values['water_level'] > 20,  # Activar bomba si el nivel de agua es suficiente (> 20%)
            'abrir_valvula': decision_riego == 1,  # Abrir la válvula si se decide activar el riego
            'inyeccion_fertilizante': sensor_values['ce'] < 1.5  # Inyectar fertilizante si la CE es baja (< 1.5 mS/cm)
        }

        # Imprimimos el resultado de la decisión para fines de depuración
        print(f"Decisión tomada: {decision}")
        return decision
