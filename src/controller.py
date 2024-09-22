# controller.py

from sensors import HumiditySensor, PhSensor, CESensor, LevelSensor
from actuators import PumpControl, ValveControl, FertilizerInjector
from signal_conditioning import SignalConditioning
from decision_engine import DecisionEngine
from cloud_sync import CloudSync
from model_training import ModelTraining
from gui import NodeRedInterface

import time
import logging
import threading
import os
import csv
import sys
import requests
from datetime import datetime

# Configuración del logging para registrar eventos y errores
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


class ControladorSistemaRiego:
    """
    Clase principal que controla el sistema de riego automatizado.
    Se encarga de la adquisición de datos, toma de decisiones, control de actuadores,
    sincronización con la nube y actualización de la interfaz gráfica.
    """

    def __init__(self):
        # Inicialización de sensores con parámetros de calibración y canales
        self.humidity_sensor = HumiditySensor(channel=0, calibration_params={
            'min_adc': 5000, 'max_adc': 25000, 'min_humidity': 0.0, 'max_humidity': 100.0
        })
        self.ph_sensor = PhSensor(channel=1, calibration_params={
            'min_adc': 0, 'max_adc': 32767, 'slope': -5.70, 'intercept': 21.34
        })
        self.ce_sensor = CESensor(channel=2, calibration_params={
            'min_adc': 4000, 'max_adc': 26000, 'min_ce': 0.0, 'max_ce': 5.0
        })
        self.level_sensor = LevelSensor(channel=3, calibration_params={
            'min_adc': 3000, 'max_adc': 27000, 'min_level': 0.0, 'max_level': 100.0
        })

        # Acondicionamiento de señal
        self.signal_conditioning = SignalConditioning()

        # Motor de toma de decisiones (modelo de Machine Learning)
        self.decision_engine = DecisionEngine(model_path='data/modelo_actualizado.pkl')

        # Sincronización con la nube
        self.cloud_sync = CloudSync(credentials_path='config/credentials.json')

        # Entrenamiento y actualización del modelo
        self.model_training = ModelTraining()

        # Interfaz gráfica (GUI) en Node-RED
        self.gui = NodeRedInterface()

        # Parámetros del sistema
        self.data_collection_frequency = 60 # Frecuencia de recolección de datos en segundos
        self.sensor_data = []  # Lista para almacenar datos sensoriales

        # Estado del sistema
        self.online_mode = False  # Indica si hay conexión a internet
        self.control_mode = 'automatic'  # 'automatic' o 'manual'

        # Definir pines GPIO para los actuadores
        GPIO_PINS = {
            'bomba': 17,
            'valvula_riego': 27,
            'valvula_suministro': 23,
            'valvula_fertilizante': 22
        }

        # Inicialización de actuadores con los pines GPIO

        # Inicializar la bomba hidráulica
        self.pump_control = PumpControl(GPIO_PINS['bomba'])

        # Inicializar las válvulas (excepto la de fertilizante)
        self.valve_control = ValveControl({
            'riego': GPIO_PINS['valvula_riego'],
            'suministro_alternativo': GPIO_PINS['valvula_suministro']
        })

        # Inicialización del inyector de fertilizante (válvula ON/OFF)
        self.fertilizer_injector = FertilizerInjector(GPIO_PINS['valvula_fertilizante'])

        # Determinar si estamos en modo de simulación
        self.simulation_mode = sys.platform == "win32"

        logging.info("Controlador del Sistema de Riego inicializado.")

    def iniciar(self):
        """
        Método principal que inicia el ciclo de control del sistema de riego.
        Realiza la adquisición de datos, procesamiento, actualización de la interfaz
        y sincronización con la nube en un bucle infinito.
        """
        logging.info("Iniciando el sistema de riego...")
        while True:
            try:
                # 1. Adquisición de datos de sensores
                sensor_values = self._leer_sensores()

                # 2. Verificar conexión a internet y sincronizar si es posible
                self.online_mode = self._verificar_conexion_internet()
                if self.online_mode:
                    # Sincronizar con la nube en un hilo separado para no bloquear el ciclo principal
                    threading.Thread(target=self._sincronizar_con_nube, args=(sensor_values,)).start()
                else:
                    logging.info("Operando en modo offline.")

                # 3. Procesar los datos con la lógica de toma de decisiones
                decision = self._tomar_decision(sensor_values)

                # 4. Accionar los actuadores según la decisión
                self._accionar_actuadores(decision)

                # 5. Actualizar la interfaz gráfica con los nuevos datos y estado del sistema
                self.gui.actualizar_interfaz(sensor_values, self.control_mode)

                # 6. Esperar hasta la próxima iteración
                time.sleep(self.data_collection_frequency)

            except Exception as e:
                logging.error(f"Error en el ciclo principal: {e}")
                # Esperar unos segundos antes de intentar de nuevo para evitar bucles rápidos de error
                time.sleep(5)

    def _leer_sensores(self):
        """
        Adquiere los datos de todos los sensores.
        """
        logging.info("Leyendo datos de sensores...")
        try:
            # Lectura de los sensores (valores calibrados)
            humidity = self.humidity_sensor.leer()
            ph = self.ph_sensor.leer()
            ce = self.ce_sensor.leer()
            water_level = self.level_sensor.leer()

            # Acondicionamiento de señal
            humidity = self.signal_conditioning.acondicionar_humedad(humidity)
            ph = self.signal_conditioning.acondicionar_ph(ph)
            ce = self.signal_conditioning.acondicionar_ce(ce)
            water_level = self.signal_conditioning.acondicionar_nivel(water_level)

            # Obtener el timestamp actual
            timestamp = time.time()

            # Agrupar datos en un diccionario con marca de tiempo
            sensor_values = {
                'timestamp': timestamp,
                'humidity': round(humidity, 1),
                'ph': round(ph, 1),
                'ce': round(ce, 1),
                'water_level': round(water_level, 1)
            }

            logging.info(f"Datos adquiridos: {sensor_values}")

            # Almacenar datos localmente
            self.sensor_data.append(sensor_values)

            # Guardar los datos en los archivos CSV
            self._guardar_datos_csv(sensor_values)

            return sensor_values

        except Exception as e:
            logging.error(f"Error al leer sensores: {e}")
            raise

    def _guardar_datos_csv(self, sensor_values):
        # Ruta del archivo CSV
        csv_file = 'data/sensor_data.csv'
        file_exists = os.path.isfile(csv_file)

        # Convertir timestamp a formato legible sin modificar sensor_values
        timestamp_str = datetime.fromtimestamp(sensor_values['timestamp']).strftime('%Y-%m-%d %H:%M:%S')

        # Crear una copia de sensor_values para escribir al CSV
        sensor_values_csv = sensor_values.copy()
        sensor_values_csv['timestamp'] = timestamp_str

        # Campos del CSV
        campos = ['timestamp', 'humidity', 'ph', 'ce', 'water_level']

        try:
            # Escribir en el CSV usando sensor_values_csv
            with open(csv_file, mode='a', newline='') as archivo_csv:
                escritor = csv.DictWriter(archivo_csv, fieldnames=campos)
                if not file_exists:
                    escritor.writeheader()
                escritor.writerow(sensor_values_csv)
            logging.info("Datos guardados en sensor_data.csv")
        except Exception as e:
            logging.error(f"Error al guardar datos en CSV: {e}")
            raise

    def _verificar_conexion_internet(self):
        """
        Verifica la conexión a internet intentando acceder a un servicio conocido.
        Retorna True si hay conexión, False de lo contrario.
        """
        try:
            requests.get('https://www.google.com', timeout=5)
            return True
        except (requests.ConnectionError, requests.Timeout):
            return False

    def _tomar_decision(self, sensor_values):
        """
        Toma decisiones basadas en los datos de los sensores y la lógica definida.
        """
        logging.info("Procesando datos y tomando decisiones...")
        try:
            # Obtener el modo de control desde la interfaz
            self.control_mode = self.gui.obtener_modo_control()
            logging.info(f"Modo de control actual: {self.control_mode}")

            # Si el modo es manual, no se toman decisiones automáticas
            if self.control_mode == 'manual':
                logging.info("Modo manual activo. No se tomarán decisiones automáticas.")
                return {}

            # Evaluar umbrales críticos
            umbrales_ok = self._verificar_umbrales(sensor_values)

            if not umbrales_ok:
                logging.warning("Datos fuera de umbrales permitidos. Tomando acciones de emergencia.")
                decision = self._acciones_emergencia(sensor_values)
            else:
                # Utilizar el motor de decisiones (Machine Learning) para tomar decisiones
                decision = self.decision_engine.evaluar(sensor_values)

            # Guardar la decisión en un archivo CSV
            self._guardar_decision_csv(sensor_values, decision)

            return decision

        except Exception as e:
            logging.error(f"Error al tomar decisiones: {e}")
            raise

    def _accionar_actuadores(self, decision):
        """
        Controla los actuadores según la decisión tomada.
        """
        try:
            # Control de la bomba hidráulica
            if decision.get('activar_bomba'):
                self.pump_control.activar()
            else:
                self.pump_control.desactivar()

            # Control de la válvula de riego
            if decision.get('abrir_valvula_riego'):
                self.valve_control.abrir_valvula('riego')
            else:
                self.valve_control.cerrar_valvula('riego')

            # Control del inyector de fertilizante
            if decision.get('inyectar_fertilizante'):
                self.fertilizer_injector.activar()
            else:
                self.fertilizer_injector.desactivar()

            # Control de la válvula de suministro alternativo (PUCP)
            if decision.get('abrir_valvula_suministro'):
                self.valve_control.abrir_valvula('suministro_alternativo')
            else:
                self.valve_control.cerrar_valvula('suministro_alternativo')

            logging.info(f"Acciones ejecutadas: {decision}")

        except Exception as e:
            logging.error(f"Error al accionar actuadores: {e}")
            raise

    def _verificar_umbrales(self, sensor_values):
        """
        Verifica si los datos de los sensores están dentro de los umbrales permitidos.
        Retorna True si todos los valores están dentro de los límites, False de lo contrario.
        """
        UMBRALES = {
            'humidity': {'min': 20, 'max': 80},
            'ph': {'min': 5.5, 'max': 7.5},
            'ce': {'min': 1.0, 'max': 2.5},
            'water_level': {'min': 20, 'max': 80}
        }

        umbrales_ok = True
        for sensor, limits in UMBRALES.items():
            value = sensor_values.get(sensor)
            if value is None:
                continue
            if not (limits['min'] <= value <= limits['max']):
                logging.warning(f"{sensor} fuera de umbrales: {value} (Límites: {limits})")
                umbrales_ok = False

        return umbrales_ok

    def _acciones_emergencia(self, sensor_values):
        """
        Toma acciones correctivas inmediatas cuando los datos están fuera de los umbrales permitidos.
        """
        decision = {}

        try:
            # Acciones de emergencia para humedad
            if sensor_values['humidity'] < 20:
                decision['activar_bomba'] = True
                decision['abrir_valvula_riego'] = True
                logging.info("Emergencia: Humedad muy baja. Activando riego.")
            elif sensor_values['humidity'] > 80:
                decision['activar_bomba'] = False
                decision['abrir_valvula_riego'] = False
                logging.info("Emergencia: Humedad muy alta. Desactivando riego.")

            # Acciones de emergencia para pH
            if sensor_values['ph'] < 5.5:
                decision['inyectar_fertilizante'] = True
                logging.info("Emergencia: pH muy bajo. Inyectando solución alcalina.")
            elif sensor_values['ph'] > 7.5:
                decision['inyectar_fertilizante'] = True
                logging.info("Emergencia: pH muy alto. Inyectando solución ácida.")

            # Acciones de emergencia para CE
            if sensor_values['ce'] < 1.0:
                decision['inyectar_fertilizante'] = True
                logging.info("Emergencia: CE muy baja. Inyectando fertilizante.")
            elif sensor_values['ce'] > 2.5:
                decision['abrir_valvula_suministro'] = True
                logging.info("Emergencia: CE muy alta. Diluyendo solución.")

            # Acciones de emergencia para nivel de agua
            if sensor_values['water_level'] < 20:
                decision['abrir_valvula_suministro'] = True
                logging.info("Emergencia: Nivel de agua bajo. Abriendo suministro alternativo.")
            elif sensor_values['water_level'] > 80:
                decision['abrir_valvula_suministro'] = False
                logging.info("Nivel de agua adecuado. Cerrando suministro alternativo.")

            return decision

        except Exception as e:
            logging.error(f"Error en acciones de emergencia: {e}")
            raise

    def _guardar_decision_csv(self, sensor_values, decision):
        decision_csv = 'data/decision_data.csv'
        file_exists = os.path.isfile(decision_csv)

        # Convertir timestamp a formato legible sin modificar sensor_values
        timestamp_str = datetime.fromtimestamp(sensor_values['timestamp']).strftime('%Y-%m-%d %H:%M:%S')

        # Combinar sensor_values y decision en un solo diccionario
        data = {**sensor_values, **decision}

        # Crear una copia para escribir en el CSV
        data_csv = data.copy()
        data_csv['timestamp'] = timestamp_str

        # Campos del CSV
        campos = ['timestamp', 'humidity', 'ph', 'ce', 'water_level',
                'activar_bomba', 'abrir_valvula_riego', 'inyectar_fertilizante', 'abrir_valvula_suministro']

       
        for key in ['activar_bomba', 'abrir_valvula_riego', 'inyectar_fertilizante', 'abrir_valvula_suministro']:
            if key not in data_csv or data_csv[key] is None:
                data_csv[key] = False 

        try:
            # Escribir en el CSV usando data_csv
            with open(decision_csv, mode='a', newline='') as archivo_csv:
                escritor = csv.DictWriter(archivo_csv, fieldnames=campos)
                if not file_exists:
                    escritor.writeheader()
                escritor.writerow(data_csv)

            logging.info("Decisión guardada en decision_data.csv.")

        except Exception as e:
            logging.error(f"Error al guardar decisión en CSV: {e}")
            raise

    def _sincronizar_con_nube(self, sensor_values):
        """
        Sincroniza los datos locales con la nube y actualiza el modelo de Machine Learning si hay
        una versión más reciente disponible en la nube.
        """
        try:
            # Enviar datos sensoriales a la nube para almacenamiento y análisis
            self.cloud_sync.enviar_datos(sensor_values)

            # Actualizar el modelo desde la nube si hay uno nuevo disponible
            modelo_nuevo = self.cloud_sync.obtener_modelo_actualizado()
            if modelo_nuevo:
                self.decision_engine.actualizar_modelo(modelo_nuevo)
                logging.info("Modelo de Machine Learning actualizado desde la nube.")

            # Iniciar entrenamiento en la nube con nuevos datos
            threading.Thread(target=self.model_training.entrenar_modelo_en_nube).start()

        except Exception as e:
            logging.error(f"Error en sincronización con la nube: {e}")
            # Implementar reintentos o manejo de fallos según sea necesario


