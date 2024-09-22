# decision_engine.py

import os
import pickle
import logging
import numpy as np
import pandas as pd

# Configuración del logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


class DecisionEngine:
    """
    Clase que representa el motor de toma de decisiones del sistema de riego.
    Utiliza un modelo de Machine Learning (Random Forest) para predecir acciones
    y aplica reglas de negocio adicionales.
    """
    def __init__(self, model_path="data/modelo_actualizado.pkl"):
        """
        Inicializa el motor de toma de decisiones cargando el modelo entrenado.

        :param model_path: Ruta del archivo donde se encuentra el modelo entrenado.
        """
        self.model_path = model_path
        self.model = None
        self.umbrales = {
            'humidity': {'min': 20, 'max': 80},
            'ph': {'min': 5.5, 'max': 7.5},
            'ce': {'min': 1.0, 'max': 2.5},
            'water_level': {'min': 20, 'max': 80}
        }
        self.cargar_modelo()
        logging.info("Motor de Toma de Decisiones inicializado.")

    def cargar_modelo(self):
        """
        Carga el modelo entrenado desde un archivo local.
        """
        try:
            logging.info("Cargando modelo de Machine Learning desde archivo local...")
            with open(self.model_path, "rb") as f:
                self.model = pickle.load(f)
            logging.info("Modelo cargado exitosamente.")
        except FileNotFoundError:
            logging.warning(f"Archivo de modelo no encontrado en {self.model_path}. Continuando sin modelo en modo simulación.")
            self.model = None
        except Exception as e:
            logging.warning(f"No se pudo cargar el modelo. Continuando sin modelo en modo simulación. Detalle: {e}")
            self.model = None

    def actualizar_modelo(self, nuevo_modelo):
        """
        Actualiza el modelo de Machine Learning con uno nuevo proporcionado.

        :param nuevo_modelo: Modelo entrenado a reemplazar.
        """
        self.model = nuevo_modelo
        logging.info("Modelo de Machine Learning actualizado.")

    def evaluar(self, sensor_values):
        """
        Toma una decisión basada en los valores de los sensores actuales y el modelo de ML.

        :param sensor_values: Diccionario con los valores de los sensores.
        :return: Diccionario con las decisiones de activación de actuadores.
        """
        logging.info("Procesando decisión basada en los valores de sensores...")

        # Verificar si el modelo está cargado
        if self.model is None:
            logging.warning("No hay un modelo cargado. Utilizando lógica basada en umbrales.")
            return self._decisiones_por_defecto(sensor_values)

        try:
            # Preparar los datos de entrada para el modelo
            features = ['humidity', 'ph', 'ce', 'water_level']
            entrada = pd.DataFrame([sensor_values])[features]

            # Realizar la predicción
            decision_riego = self.model.predict(entrada)[0]

            # Generar decisiones basadas en el modelo y reglas adicionales
            decision = self._generar_decisiones(decision_riego, sensor_values)

            logging.info(f"Decisión tomada: {decision}")
            return decision

        except Exception as e:
            logging.error(f"Error al tomar decisión: {e}")
            # En caso de error, podemos optar por decisiones por defecto o acciones seguras
            return self._decisiones_por_defecto(sensor_values)

    def _generar_decisiones(self, decision_riego, sensor_values):
        """
        Genera las decisiones de activación de actuadores basadas en la predicción del modelo
        y reglas de negocio adicionales.

        :param decision_riego: Resultado de la predicción del modelo (1 - regar, 0 - no regar).
        :param sensor_values: Diccionario con los valores de los sensores.
        :return: Diccionario con las decisiones de activación.
        """
        # Inicializar decisiones
        decision = {
            'activar_bomba': False,
            'abrir_valvula_riego': False,
            'inyectar_fertilizante': False,
            'abrir_valvula_suministro': False
        }

        # Decisión de riego basada en el modelo
        if decision_riego == 1 and sensor_values['humidity'] < self.umbrales['humidity']['max']:
            decision['activar_bomba'] = True
            decision['abrir_valvula_riego'] = True
            logging.info("Decisión: Activar riego basado en predicción del modelo.")
        else:
            logging.info("Decisión: No es necesario regar según el modelo.")

        # Decisión sobre fertilizante basada en CE
        if sensor_values['ce'] < self.umbrales['ce']['min']:
            decision['inyectar_fertilizante'] = True
            logging.info("Decisión: Inyectar fertilizante debido a CE baja.")
        elif sensor_values['ce'] > self.umbrales['ce']['max']:
            decision['inyectar_fertilizante'] = False
            logging.info("Decisión: No inyectar fertilizante debido a CE alta.")

        # Decisión sobre suministro alternativo de agua
        if sensor_values['water_level'] < self.umbrales['water_level']['min']:
            decision['abrir_valvula_suministro'] = True
            logging.info("Decisión: Abrir suministro alternativo debido a nivel de agua bajo.")
        elif sensor_values['water_level'] > self.umbrales['water_level']['max']:
            decision['abrir_valvula_suministro'] = False
            logging.info("Decisión: Cerrar suministro alternativo debido a nivel de agua adecuado.")

        return decision

    def generar_sugerencias(self, sensor_values):
        """
        Genera sugerencias para el operador cuando el sistema está en modo manual.

        :param sensor_values: Diccionario con los valores de los sensores.
        :return: Diccionario con las sugerencias.
        """
        logging.info("Generando sugerencias basadas en los valores de sensores...")

        try:
            # Utilizar el mismo proceso que en evaluar, pero formateado para sugerencias
            decision = self.evaluar(sensor_values)

            # Formatear las sugerencias para presentarlas al operador
            sugerencias = {
                'accion_recomendada': 'Regar' if decision.get('abrir_valvula_riego') else 'No regar',
                'ajuste_fertilizante': 'Inyectar fertilizante' if decision.get('inyectar_fertilizante') else 'No inyectar fertilizante',
                'ajuste_suministro': 'Abrir suministro alternativo' if decision.get('abrir_valvula_suministro') else 'Cerrar suministro alternativo',
                'comentarios': self._generar_comentarios(sensor_values)
            }

            logging.info(f"Sugerencias generadas: {sugerencias}")
            return sugerencias

        except Exception as e:
            logging.error(f"Error al generar sugerencias: {e}")
            return None

    def _generar_comentarios(self, sensor_values):
        """
        Genera comentarios adicionales basados en los valores de los sensores.

        :param sensor_values: Diccionario con los valores de los sensores.
        :return: Lista de comentarios.
        """
        comentarios = []
        # Verificar si los valores están cerca de los umbrales críticos
        for sensor, limites in self.umbrales.items():
            valor = sensor_values.get(sensor)
            if valor is None:
                continue
            if valor < limites['min']:
                comentarios.append(f"El valor de {sensor} está por debajo del límite mínimo.")
            elif valor > limites['max']:
                comentarios.append(f"El valor de {sensor} supera el límite máximo.")
        return comentarios

    def _decisiones_por_defecto(self, sensor_values):
        """
        Genera decisiones por defecto basadas en los umbrales cuando no se puede utilizar el modelo.

        :param sensor_values: Diccionario con los valores de los sensores.
        :return: Diccionario con las decisiones de activación.
        """
        logging.info("Generando decisiones basadas en umbrales debido a la falta de modelo.")

        decision = {
            'activar_bomba': False,
            'abrir_valvula_riego': False,
            'inyectar_fertilizante': False,
            'abrir_valvula_suministro': False
        }

        # Lógica de riego basada en humedad
        if sensor_values['humidity'] < self.umbrales['humidity']['min']:
            decision['activar_bomba'] = True
            decision['abrir_valvula_riego'] = True
            logging.info("Decisión: Activar riego basado en humedad baja.")
        else:
            logging.info("Decisión: No es necesario regar basado en humedad.")

        # Lógica de fertilizante basada en CE
        if sensor_values['ce'] < self.umbrales['ce']['min']:
            decision['inyectar_fertilizante'] = True
            logging.info("Decisión: Inyectar fertilizante basado en CE baja.")
        elif sensor_values['ce'] > self.umbrales['ce']['max']:
            decision['inyectar_fertilizante'] = False
            logging.info("Decisión: No inyectar fertilizante basado en CE alta.")

        # Lógica de suministro alternativo basada en nivel de agua
        if sensor_values['water_level'] < self.umbrales['water_level']['min']:
            decision['abrir_valvula_suministro'] = True
            logging.info("Decisión: Abrir suministro alternativo basado en nivel de agua bajo.")
        elif sensor_values['water_level'] > self.umbrales['water_level']['max']:
            decision['abrir_valvula_suministro'] = False
            logging.info("Decisión: Cerrar suministro alternativo basado en nivel de agua adecuado.")

        return decision

    def verificar_umbrales(self, sensor_values):
        """
        Verifica si los valores de los sensores están dentro de los umbrales permitidos.

        :param sensor_values: Diccionario con los valores de los sensores.
        :return: True si todos los valores están dentro de los límites, False de lo contrario.
        """
        umbrales_ok = True
        for sensor, limites in self.umbrales.items():
            valor = sensor_values.get(sensor)
            if valor is None:
                continue
            if not (limites['min'] <= valor <= limites['max']):
                logging.warning(f"{sensor} fuera de umbrales: {valor} (Límites: {limites})")
                umbrales_ok = False
        return umbrales_ok


