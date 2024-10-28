# decision_engine.py

import os
import pickle
import logging
import numpy as np
import pandas as pd
from datetime import datetime

# Configuración del logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

class DecisionEngine:
    """
    Clase que representa el motor de toma de decisiones del sistema de riego.
    Utiliza un modelo de Machine Learning para predecir acciones.
    """

    def __init__(self, model_path="data/modelo_actualizado.pkl"):
        """
        Inicializa el motor de toma de decisiones cargando el modelo entrenado.

        :param model_path: Ruta del archivo donde se encuentra el modelo entrenado.
        """
        self.model_path = model_path
        self.model = None
        self.scaler = None
        self.features = None
        self.umbrales = None  # Umbrales se establecerán dinámicamente según la estación
        self.cargar_modelo()
        logging.info("Motor de Toma de Decisiones inicializado.")

    def cargar_modelo(self):
        """
        Carga el modelo entrenado desde un archivo local.
        """
        try:
            logging.info("Cargando modelo de Machine Learning desde archivo local...")
            with open(self.model_path, "rb") as f:
                model_data = pickle.load(f)
                self.model = model_data['model']
                self.scaler = model_data['scaler']
                self.features = model_data['features']
            logging.info("Modelo cargado exitosamente.")
        except FileNotFoundError:
            logging.warning(f"Archivo de modelo no encontrado en {self.model_path}. Continuando con el modelo anterior.")
            # Mantener el modelo anterior si existe
        except Exception as e:
            logging.warning(f"No se pudo cargar el modelo. Continuando con el modelo anterior. Detalle: {e}")
            # Mantener el modelo anterior si existe

    def actualizar_modelo(self):
        """
        Actualiza el modelo de Machine Learning cargándolo nuevamente desde el archivo.
        """
        self.cargar_modelo()
        logging.info("Modelo de Machine Learning actualizado.")

    def evaluar(self, sensor_values):
        logging.info("Procesando decisión basada en los valores de sensores...")

        # Obtener la estación actual
        season = sensor_values.get('season', 'unknown')

        # Establecer umbrales según la estación
        self.umbrales = self._definir_umbrales_por_estacion(season)

        # Verificar si los datos de sensores están dentro de los umbrales permitidos
        umbrales_ok = self.verificar_umbrales(sensor_values)

        if not umbrales_ok:
            logging.warning("Datos fuera de umbrales permitidos. Tomando acciones de emergencia.")
            decision = self.acciones_emergencia(sensor_values)
            return decision
        else:
            # Verificar si el modelo está cargado
            if self.model is None or self.scaler is None or self.features is None:
                logging.warning("No hay un modelo cargado. Utilizando lógica basada en umbrales.")
                decision = self._decisiones_por_defecto(sensor_values)
                return decision

            try:
                # Preparar los datos de entrada para el modelo
                entrada = pd.DataFrame([sensor_values])

                # Manejar valores faltantes
                entrada = entrada.ffill().bfill()

                # Eliminar 'timestamp' antes de cualquier procesamiento
                if 'timestamp' in entrada.columns:
                    entrada = entrada.drop(columns=['timestamp'])

                # Convertir la columna 'season' a variables dummy sin eliminar ninguna categoría
                if 'season' in entrada.columns:
                    entrada = pd.get_dummies(entrada, columns=['season'], drop_first=False)
                else:
                    logging.warning("La columna 'season' no está presente en los datos de entrada.")


                # Añadir columnas faltantes con valor cero
                for col in self.features:
                    if col not in entrada.columns:
                        entrada[col] = 0  # Añadir las columnas faltantes como cero

                missing_features = set(self.features) - set(entrada.columns)
                if missing_features:
                    logging.warning(f"Características faltantes en los datos de entrada: {missing_features}")
                    for feature in missing_features:
                        entrada[feature] = 0

                # Reordenar las columnas según self.features
                entrada = entrada[self.features]

                # Escalar los datos de entrada
                entrada_scaled = self.scaler.transform(entrada)

                # Realizar la predicción
                prediccion = self.model.predict(entrada_scaled)

                # Validar Formato de las Predicciones
                if isinstance(prediccion, np.ndarray):
                    if prediccion.ndim == 1 and len(prediccion) == 2:
                        porcentaje_fertilizante, cantidad_agua = prediccion
                    elif prediccion.ndim == 2 and prediccion.shape == (1, 2):
                        porcentaje_fertilizante, cantidad_agua = prediccion[0]
                    else:
                        logging.error("Formato de predicción inesperado del modelo.")
                        # Manejar el error: usar decisiones por defecto
                        return self._decisiones_por_defecto(sensor_values)
                    # Asegurar que los valores no sean negativos
                    porcentaje_fertilizante = max(0, porcentaje_fertilizante)
                    cantidad_agua = max(0, cantidad_agua)
                else:
                    logging.error("La predicción del modelo no es un ndarray.")
                    # Manejar el error: usar decisiones por defecto
                    return self._decisiones_por_defecto(sensor_values)

                # Generar decisiones basadas en la predicción y reglas adicionales
                decision = self._generar_decisiones(porcentaje_fertilizante, cantidad_agua, sensor_values)

                logging.info(f"Decisión tomada: {decision}")
                return decision

            except Exception as e:
                logging.exception("Error al tomar decisión:")
                # En caso de error, podemos optar por decisiones por defecto o acciones seguras
                return self._decisiones_por_defecto(sensor_values)

    def verificar_umbrales(self, sensor_values):
        """
        Verifica si los valores de los sensores están dentro de los umbrales permitidos.

        :param sensor_values: Diccionario con los valores de los sensores.
        :return: True si todos los valores están dentro de los límites, False de lo contrario.
        """
        umbrales_ok = True
        for sensor, limits in self.umbrales.items():
            value = sensor_values.get(sensor)
            if value is None:
                continue
            if not (limits['min'] <= value <= limits['max']):
                logging.warning(f"{sensor} fuera de umbrales: {value} (Límites: {limits})")
                umbrales_ok = False
        return umbrales_ok

    def acciones_emergencia(self, sensor_values):
        """
        Toma acciones correctivas inmediatas cuando los datos están fuera de los umbrales permitidos.
        """
        decision = {
            'activar_bomba': False,
            'abrir_valvula_riego': False,
            'inyectar_fertilizante': False,
            'abrir_valvula_suministro': False,
            'porcentaje_fertilizante': 0,
            'cantidad_agua': 0
        }

        try:
            # Acciones de emergencia para humedad
            if sensor_values.get('humidity', 0) < self.umbrales['humidity']['min']:
                decision['activar_bomba'] = True
                decision['abrir_valvula_riego'] = True
                decision['cantidad_agua'] = 10  # Valor por defecto
                logging.info("Emergencia: Humedad muy baja. Activando riego.")
            elif sensor_values.get('humidity', 100) > self.umbrales['humidity']['max']:
                decision['activar_bomba'] = False
                decision['abrir_valvula_riego'] = False
                logging.info("Emergencia: Humedad muy alta. Desactivando riego.")

            # Acciones de emergencia para temperatura
            if sensor_values.get('temperature', 0) > self.umbrales['temperature']['max']:
                # Temperatura muy alta
                decision['activar_bomba'] = True  # Activamos riego para enfriar el suelo
                decision['abrir_valvula_riego'] = True
                decision['cantidad_agua'] = 10  # Valor por defecto
                logging.info("Emergencia: Temperatura muy alta. Activando riego para enfriar el suelo.")
            elif sensor_values.get('temperature', 100) < self.umbrales['temperature']['min']:
                # Temperatura muy baja
                decision['activar_bomba'] = False  # Reducimos riego para evitar enfriar más el suelo
                decision['abrir_valvula_riego'] = False
                logging.info("Emergencia: Temperatura muy baja. Desactivando riego para evitar enfriar el suelo.")

            # Acciones de emergencia para pH
            if sensor_values.get('ph', 7) < self.umbrales['ph']['min']:
                decision['inyectar_fertilizante'] = True
                decision['porcentaje_fertilizante'] = 5  # Ajustar según necesidad
                logging.info("Emergencia: pH muy bajo. Inyectando solución alcalina.")
            elif sensor_values.get('ph', 7) > self.umbrales['ph']['max']:
                decision['inyectar_fertilizante'] = True
                decision['porcentaje_fertilizante'] = 5  # Ajustar según necesidad
                logging.info("Emergencia: pH muy alto. Inyectando solución ácida.")

            # Acciones de emergencia para CE
            if sensor_values.get('ce', 0) < self.umbrales['ce']['min']:
                decision['inyectar_fertilizante'] = True
                decision['porcentaje_fertilizante'] = 10  # Ajustar según necesidad
                logging.info("Emergencia: CE muy baja. Inyectando fertilizante.")
            elif sensor_values.get('ce', 100) > self.umbrales['ce']['max']:
                decision['abrir_valvula_suministro'] = True
                logging.info("Emergencia: CE muy alta. Diluyendo solución.")

            # Acciones de emergencia para nivel de agua
            if 'water_level' in sensor_values:
                if sensor_values['water_level'] < self.umbrales['water_level']['min']:
                    decision['abrir_valvula_suministro'] = True
                    logging.info("Emergencia: Nivel de agua bajo. Abriendo suministro alternativo.")
                elif sensor_values['water_level'] > self.umbrales['water_level']['max']:
                    decision['abrir_valvula_suministro'] = False
                    logging.info("Nivel de agua adecuado. Cerrando suministro alternativo.")

            return decision

        except Exception:
            logging.exception("Error en acciones de emergencia:")
            raise

    def _definir_umbrales_por_estacion(self, season):
        """
        Define los umbrales de los sensores según la estación del año.

        :param season: Estación del año ('summer', 'autumn', 'winter', 'spring', 'unknown')
        :return: Diccionario de umbrales
        """
        if season == 'summer':
            UMBRALES = {
                'humidity': {'min': 20, 'max': 80},
                'temperature': {'min': 15, 'max': 40},
                'ph': {'min': 5.5, 'max': 7.5},
                'ce': {'min': 1.0, 'max': 2.5},
                'water_level': {'min': 20, 'max': 80},
                'flow_rate': {'min': 0.0, 'max': 60.0}
            }
        elif season == 'autumn':
            UMBRALES = {
                'humidity': {'min': 25, 'max': 75},
                'temperature': {'min': 10, 'max': 30},
                'ph': {'min': 5.5, 'max': 7.5},
                'ce': {'min': 1.0, 'max': 2.5},
                'water_level': {'min': 20, 'max': 80},
                'flow_rate': {'min': 0.0, 'max': 60.0}
            }
        elif season == 'winter':
            UMBRALES = {
                'humidity': {'min': 30, 'max': 70},
                'temperature': {'min': 5, 'max': 25},
                'ph': {'min': 5.5, 'max': 7.5},
                'ce': {'min': 1.0, 'max': 2.5},
                'water_level': {'min': 20, 'max': 80},
                'flow_rate': {'min': 0.0, 'max': 60.0}
            }
        elif season == 'spring':
            UMBRALES = {
                'humidity': {'min': 25, 'max': 75},
                'temperature': {'min': 10, 'max': 30},
                'ph': {'min': 5.5, 'max': 7.5},
                'ce': {'min': 1.0, 'max': 2.5},
                'water_level': {'min': 20, 'max': 80},
                'flow_rate': {'min': 0.0, 'max': 60.0}
            }
        else:
            # Por defecto
            UMBRALES = {
                'humidity': {'min': 20, 'max': 80},
                'temperature': {'min': 10, 'max': 35},
                'ph': {'min': 5.5, 'max': 7.5},
                'ce': {'min': 1.0, 'max': 2.5},
                'water_level': {'min': 20, 'max': 80},
                'flow_rate': {'min': 0.0, 'max': 60.0}
            }
        return UMBRALES

    def _generar_decisiones(self, porcentaje_fertilizante, cantidad_agua, sensor_values):
        """
        Genera las decisiones de activación de actuadores basadas en la predicción del modelo
        y reglas de negocio adicionales.

        :param porcentaje_fertilizante: Porcentaje de fertilizante a aplicar.
        :param cantidad_agua: Cantidad de agua a aplicar (litros).
        :param sensor_values: Diccionario con los valores de los sensores.
        :return: Diccionario con las decisiones de activación.
        """
        # Inicializar decisiones
        decision = {
            'activar_bomba': False,
            'abrir_valvula_riego': False,
            'inyectar_fertilizante': False,
            'abrir_valvula_suministro': False,
            'porcentaje_fertilizante': 0,
            'cantidad_agua': 0
        }

        # Decisión de riego basada en cantidad de agua
        if cantidad_agua > 0 and sensor_values.get('humidity', 100) < self.umbrales['humidity']['max']:
            decision['activar_bomba'] = True
            decision['abrir_valvula_riego'] = True
            decision['cantidad_agua'] = cantidad_agua
            logging.info(f"Decisión: Activar riego y aplicar {cantidad_agua:.2f} litros de agua.")

        # Decisión sobre fertilizante
        if porcentaje_fertilizante > 0:
            decision['inyectar_fertilizante'] = True
            decision['porcentaje_fertilizante'] = porcentaje_fertilizante
            logging.info(f"Decisión: Inyectar fertilizante al {porcentaje_fertilizante:.2f}%.")
        else:
            logging.info("Decisión: No es necesario inyectar fertilizante.")

        # Decisión sobre suministro alternativo de agua
        if sensor_values.get('water_level', 100) < self.umbrales['water_level']['min']:
            decision['abrir_valvula_suministro'] = True
            logging.info("Decisión: Abrir suministro alternativo debido a nivel de agua bajo.")
        else:
            decision['abrir_valvula_suministro'] = False
            logging.info("Decisión: Suministro alternativo no es necesario.")

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
                'acción recomendada': 'Regar' if decision.get('abrir_valvula_riego') else 'No regar',
                'cantidad de agua (L)': decision.get('cantidad_agua', 0),
                'inyectar fertilizante': 'Sí' if decision.get('inyectar_fertilizante') else 'No',
                'porcentaje de fertilizante (%)': decision.get('porcentaje_fertilizante', 0),
                'ajuste de suministro': 'Abrir suministro alternativo' if decision.get('abrir_valvula_suministro') else 'No abrir suministro alternativo',
                'comentarios': self._generar_comentarios(sensor_values)
            }

            logging.info(f"Sugerencias generadas: {sugerencias}")
            return sugerencias

        except Exception as e:
            logging.exception("Error al generar sugerencias:")
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
                comentarios.append(f"El valor de {sensor} ({valor}) está por debajo del límite mínimo ({limites['min']}).")
            elif valor > limites['max']:
                comentarios.append(f"El valor de {sensor} ({valor}) supera el límite máximo ({limites['max']}).")
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
            'abrir_valvula_suministro': False,
            'porcentaje_fertilizante': 0,
            'cantidad_agua': 0
        }

        # Lógica de riego basada en humedad
        if sensor_values.get('humidity', 100) < self.umbrales['humidity']['min']:
            decision['activar_bomba'] = True
            decision['abrir_valvula_riego'] = True
            decision['cantidad_agua'] = 10  # Valor por defecto
            logging.info("Decisión: Activar riego basado en humedad baja.")
        else:
            logging.info("Decisión: No es necesario regar basado en humedad.")

        # Lógica de fertilizante basada en CE
        if sensor_values.get('ce', 2.5) < self.umbrales['ce']['min']:
            decision['inyectar_fertilizante'] = True
            decision['porcentaje_fertilizante'] = 5  # Valor por defecto
            logging.info("Decisión: Inyectar fertilizante basado en CE baja.")
        elif sensor_values.get('ce', 1.0) > self.umbrales['ce']['max']:
            decision['inyectar_fertilizante'] = False
            logging.info("Decisión: No inyectar fertilizante basado en CE alta.")

        # Lógica de suministro alternativo basada en nivel de agua
        if sensor_values.get('water_level', 100) < self.umbrales['water_level']['min']:
            decision['abrir_valvula_suministro'] = True
            logging.info("Decisión: Abrir suministro alternativo basado en nivel de agua bajo.")
        else:
            decision['abrir_valvula_suministro'] = False
            logging.info("Decisión: Suministro alternativo no es necesario.")

        return decision