# controller.py

from sensors import SoilSensor, LevelSensor, FlowSensor
from actuators import PumpControl, ValveControl
from signal_conditioning import SignalConditioning
from decision_engine import DecisionEngine
from cloud_sync import CloudSync
from gui import NodeRedInterface

import time
import logging
import threading
import os
import csv
import sys
import requests
from datetime import datetime, timedelta
import schedule  # Para programar tareas
import shutil    # Para obtener información del sistema de archivos
import pandas as pd

# Configuración del logging para registrar eventos y errores
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


class ControladorSistemaRiego:
    """
    Clase principal que controla el sistema de riego automatizado.
    """

    def __init__(self):
        # Inicialización de sensores
        self.soil_sensor = SoilSensor(address=1)

        # Sensor de nivel de agua (Ultrasonido US-100)
        self.level_sensor = LevelSensor(
            trig_pin=18,  # GPIO18 para TRIG
            echo_pin=24,  # GPIO24 para ECHO
            calibration_params={
                'tank_height': 200  # Altura del tanque en cm
            }
        )

        # Inicializar sensor de flujo
        self.flow_sensor = FlowSensor(gpio_pin=17, calibration_params={
            'factor': 5.5,                    # Factor de calibración específico del sensor
            'tolerance': 0.2,                 # Tolerancia aceptable en el caudal (20%)
            'minimal_flow_threshold': 0.5     # Umbral mínimo para considerar flujo significativo
        })

        # Acondicionamiento de señal
        self.signal_conditioning = SignalConditioning()

        # Motor de toma de decisiones (modelo de Machine Learning)
        self.decision_engine = DecisionEngine(model_path='data/modelo_actualizado.pkl')

        # Sincronización con la nube
        self.cloud_sync = CloudSync(credentials_path='config/credentials.json')

        # Interfaz gráfica (GUI) en Node-RED
        self.gui = NodeRedInterface()

        # Parámetros del sistema
        self.data_collection_frequency = 60  # Frecuencia de recolección de datos en segundos
        self.sensor_data = []

        # Estado del sistema
        self.online_mode = False
        self.control_mode = 'automatic'
        self.is_busy = False  # Indica si el sistema está en una acción crítica

        # Definir pines GPIO para los actuadores
        GPIO_PINS = {
            'bomba': 25,
            'valvula_riego': 23,
            'valvula_suministro': 24,
            'valvula_fertilizante': 22
        }

        # Inicialización de actuadores
        self.pump_control = PumpControl(GPIO_PINS['bomba'])
        self.valve_control = ValveControl({
            'valvula_riego': GPIO_PINS['valvula_riego'],
            'valvula_suministro': GPIO_PINS['valvula_suministro'],
            'valvula_fertilizante': GPIO_PINS['valvula_fertilizante']
        })

        # Estados de los actuadores
        self.actuator_states = {
            'bomba': False,
            'valvula_riego': False,
            'valvula_suministro': False,
            'valvula_fertilizante': False
        }

        # Variables para programación de riego
        self.irrigation_schedule = []
        self.total_daily_water = 0
        self.remaining_daily_water = 0
        self.daily_fertilizer_percentage = 0  # Porcentaje de fertilizante diario

        # Programar horarios de riego iniciales
        self._programar_riego_diario()

        # Programar sincronización semanal con la nube en horario nocturno
        schedule.every().week.do(self._programar_sincronizacion_semanal)

        # Modo de simulación
        self.simulation_mode = sys.platform == "win32"

        # Implementación de lock para seguridad de hilos
        self.lock = threading.Lock()

        logging.info("Controlador del Sistema de Riego inicializado.")

    def iniciar(self):
        """
        Método principal que inicia el ciclo de control del sistema de riego.
        """
        logging.info("Iniciando el sistema de riego...")
        while True:
            try:
                # Ejecutar tareas programadas
                schedule.run_pending()

                # 1. Adquisición de datos de sensores
                sensor_values = self._leer_sensores()

                # 2. Verificar conexión a internet
                self.online_mode = self._verificar_conexion_internet()

                # 3. Procesar los datos con la lógica de toma de decisiones
                decision = self._tomar_decision(sensor_values)

                # 4. Accionar los actuadores según la decisión
                # No accionamos actuadores aquí si es riego programado
                if decision:
                    self._accionar_actuadores(decision)

                # 5. Detectar anomalías en el flujo de agua
                self._verificar_anomalias(sensor_values)

                # 6. Actualizar la interfaz gráfica con los nuevos datos y estado del sistema
                self.gui.actualizar_interfaz(sensor_values, self.control_mode, decision)

                # 7. Monitorear la capacidad de almacenamiento y eliminar datos antiguos si es necesario
                self._monitorear_almacenamiento()

                # 8. Esperar hasta la próxima iteración
                time.sleep(self.data_collection_frequency)

            except KeyboardInterrupt:
                logging.info("Interrupción manual del sistema.")
                break
            except Exception:
                logging.exception("Error en el ciclo principal.")
                time.sleep(5)

    def _leer_sensores(self):
        """
        Adquiere los datos de todos los sensores, los acondiciona y guarda en un CSV.
        """
        logging.info("Leyendo datos de sensores...")
        try:
            # Obtener el estado actual de la bomba y la válvula de riego
            with self.lock:
                bomba_activa = self.actuator_states.get('bomba', False)
                valvula_riego_abierta = self.actuator_states.get('valvula_riego', False)

            # Lectura del sensor de suelo
            soil_values = self.soil_sensor.leer()
            if soil_values is None:
                raise ValueError("Error al leer el sensor de suelo")

            humidity = soil_values['humidity']
            temperature = soil_values['temperature']
            ce = soil_values['ce']
            ph = soil_values['ph']

            # Leer el nivel de agua, pasando el estado de la bomba
            water_level = self.level_sensor.leer(bomba_activa=bomba_activa)

            # Leer el caudal, pasando los estados de los actuadores
            flow_rate = self.flow_sensor.leer(bomba_activa=bomba_activa, valvula_riego_abierta=valvula_riego_abierta)

            # Acondicionamiento de señal
            humidity = self.signal_conditioning.acondicionar_humedad(humidity)
            temperature = self.signal_conditioning.acondicionar_temperatura(temperature)
            ph = self.signal_conditioning.acondicionar_ph(ph)
            ce = self.signal_conditioning.acondicionar_ce(ce)
            water_level = self.signal_conditioning.acondicionar_nivel(water_level)
            # flow_rate podría acondicionarse si es necesario

            # Obtener el timestamp actual
            timestamp = time.time()

            # Obtener la estación actual
            season = self._get_current_season()

            # Agrupar datos en un diccionario
            sensor_values = {
                'timestamp': timestamp,
                'humidity': round(humidity, 1),
                'temperature': round(temperature, 1),
                'ph': round(ph, 1),
                'ce': round(ce, 1),
                'water_level': round(water_level, 1),
                'flow_rate': round(flow_rate, 1),
                'season': season
            }

            logging.info(f"Datos adquiridos: {sensor_values}")

            # Almacenar datos localmente
            self.sensor_data.append(sensor_values)

            # Guardar los datos en los archivos CSV
            self._guardar_datos_csv(sensor_values)

            return sensor_values

        except Exception:
            logging.exception("Error al leer sensores:")
            raise


    def _get_current_season(self):
        """
        Devuelve la estación actual en Perú.
        """
        month = datetime.now().month
        if month in [12, 1, 2]:
            return 'summer'
        elif month in [3, 4, 5]:
            return 'autumn'
        elif month in [6, 7, 8]:
            return 'winter'
        elif month in [9, 10, 11]:
            return 'spring'
        else:
            return 'unknown'

    def _verificar_anomalias(self, sensor_values):
        """
        Verifica si hay anomalías en el flujo de agua, indicando posibles fugas o bloqueos.
        """
        try:
            # Determinar si se espera flujo de agua basado en el estado de la bomba y válvulas
            with self.lock:
                bomba_activa = self.actuator_states.get('bomba', False)
                valvula_riego_abierta = self.actuator_states.get('valvula_riego', False)

            if bomba_activa and valvula_riego_abierta:
                # Si la bomba y la válvula están activas, se espera un flujo normal
                expected_flow = self.flow_sensor.calibration_params.get('expected_flow', 30)  # Valor promedio esperado
            else:
                # Si la bomba o la válvula están cerradas, no debería haber flujo
                expected_flow = 0  # No debería haber flujo

            # Obtener el flujo real desde sensor_values
            actual_flow = sensor_values.get('flow_rate', 0)
            # Actualizar last_reading del flow_sensor
            with self.flow_sensor.lock:
                self.flow_sensor.last_reading = actual_flow

            # Detectar fallos en el flujo
            flow_anomaly = self.flow_sensor.detectar_fallo(expected_flow)
            if flow_anomaly:
                # Ya se ha registrado el error dentro de detectar_fallo()
                pass

        except Exception:
            logging.exception("Error al verificar anomalías de flujo:")
            raise

    def _guardar_datos_csv(self, sensor_values):
        """
        Guarda los datos de sensores en un archivo CSV.
        """
        # Ruta del archivo CSV
        csv_file = 'data/sensor_data.csv'
        file_exists = os.path.isfile(csv_file)

        # Convertir timestamp a formato legible sin modificar sensor_values
        timestamp_str = datetime.fromtimestamp(sensor_values['timestamp']).strftime('%Y-%m-%d %H:%M:%S')

        # Crear una copia de sensor_values para escribir al CSV
        sensor_values_csv = sensor_values.copy()
        sensor_values_csv['timestamp'] = timestamp_str

        # Campos del CSV
        campos = ['timestamp', 'humidity', 'temperature', 'ph', 'ce', 'water_level', 'flow_rate', 'season']

        try:
            # Escribir en el CSV usando sensor_values_csv
            with open(csv_file, mode='a', newline='') as archivo_csv:
                escritor = csv.DictWriter(archivo_csv, fieldnames=campos)
                if not file_exists:
                    escritor.writeheader()
                escritor.writerow(sensor_values_csv)
            logging.info("Datos guardados en sensor_data.csv")
        except Exception:
            logging.exception("Error al guardar datos en CSV:")
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
            nuevo_modo_control = self.gui.obtener_modo_control()
            logging.info(f"Modo de control solicitado: {nuevo_modo_control}")

            # Verificar si se puede cambiar el modo de control
            with self.lock:
                if nuevo_modo_control != self.control_mode:
                    if not self.is_busy:
                        self.control_mode = nuevo_modo_control
                        logging.info(f"Modo de control cambiado a: {self.control_mode}")
                    else:
                        logging.warning("No se puede cambiar el modo de control durante una acción crítica.")

            if self.control_mode == 'manual':
                logging.info("Modo manual activo. Recibiendo comandos manuales.")
                # Recibir comandos manuales desde la interfaz
                with self.lock:
                    if not self.is_busy:
                        decision = self.gui.recibir_comandos()
                    else:
                        logging.warning("No se pueden ejecutar comandos manuales durante una acción crítica.")
                        decision = {}
            else:
                # Utilizar el motor de decisiones (Machine Learning) para tomar decisiones
                decision = self.decision_engine.evaluar(sensor_values)

                # Actualizar la cantidad total de agua y fertilizante para el día
                with self.lock:
                    self.total_daily_water = decision.get('cantidad_agua', 0)
                    self.remaining_daily_water = self.total_daily_water

                    # Actualizar el porcentaje de fertilizante
                    self.daily_fertilizer_percentage = decision.get('porcentaje_fertilizante', 0)

                # Reprogramar los horarios de riego con la nueva cantidad de agua
                self._programar_riego_diario()

                # No accionamos actuadores aquí, se hará en los eventos programados
                decision = {}  # Vaciar decisión para evitar accionar actuadores ahora

            # Guardar la decisión en un archivo CSV
            self._guardar_decision_csv(sensor_values, decision)

            return decision

        except Exception:
            logging.exception("Error al tomar decisiones:")
            raise

    def _accionar_actuadores(self, decision):
        """
        Controla los actuadores según la decisión tomada.
        """
        try:
            with self.lock:
                if self.is_busy:
                    logging.warning("El sistema está ocupado realizando una acción crítica. No se pueden accionar actuadores ahora.")
                    return

            # Control de la bomba hidráulica
            if decision.get('activar_bomba'):
                self.pump_control.activar()
                with self.lock:
                    self.actuator_states['bomba'] = True
            else:
                self.pump_control.desactivar()
                with self.lock:
                    self.actuator_states['bomba'] = False

            # Control de la válvula de riego
            if decision.get('abrir_valvula_riego'):
                self.valve_control.abrir_valvula('valvula_riego')
                with self.lock:
                    self.actuator_states['valvula_riego'] = True
            else:
                self.valve_control.cerrar_valvula('valvula_riego')
                with self.lock:
                    self.actuator_states['valvula_riego'] = False

            # Control del inyector de fertilizante
            if decision.get('inyectar_fertilizante'):
                # Ajustar la dosificación según el porcentaje de fertilizante
                porcentaje = decision.get('porcentaje_fertilizante', 0)
                self._ajustar_dosificacion_fertilizante(porcentaje)
            else:
                self.valve_control.cerrar_valvula('valvula_fertilizante')
                with self.lock:
                    self.actuator_states['valvula_fertilizante'] = False

            # Control de la válvula de suministro alternativo
            if decision.get('abrir_valvula_suministro'):
                self.valve_control.abrir_valvula('valvula_suministro')
                with self.lock:
                    self.actuator_states['valvula_suministro'] = True
            else:
                self.valve_control.cerrar_valvula('valvula_suministro')
                with self.lock:
                    self.actuator_states['valvula_suministro'] = False

            logging.info(f"Acciones ejecutadas: {decision}")

        except Exception:
            logging.exception("Error al accionar actuadores:")
            raise

    def _ajustar_dosificacion_fertilizante(self, porcentaje):
        """
        Ajusta la dosificación del fertilizante en función del porcentaje calculado.
        Controla el tiempo de apertura de la válvula de fertilizante para lograr la dosificación deseada.
        """
        try:
            with self.lock:
                if self.is_busy:
                    logging.warning("El sistema está ocupado. No se puede ajustar la dosificación de fertilizante ahora.")
                    return
                self.is_busy = True  # Iniciando acción crítica

            # Calcular el tiempo de apertura de la válvula de fertilizante en función del porcentaje
            # Suponiendo que el porcentaje es entre 0% y 100%
            # Tiempo máximo de apertura (en segundos) para 100% de fertilizante
            max_fertilizer_time = 10  # Ajustar según las características del sistema

            # Calcular el tiempo real de apertura
            tiempo_apertura = (porcentaje / 100) * max_fertilizer_time

            if tiempo_apertura > 0:
                logging.info(f"Iniciando dosificación de fertilizante por {tiempo_apertura:.2f} segundos.")

                # Abrir válvula de fertilizante
                self.valve_control.abrir_valvula('valvula_fertilizante')
                with self.lock:
                    self.actuator_states['valvula_fertilizante'] = True

                # Esperar el tiempo calculado
                time.sleep(tiempo_apertura)

                # Cerrar válvula de fertilizante
                self.valve_control.cerrar_valvula('valvula_fertilizante')
                with self.lock:
                    self.actuator_states['valvula_fertilizante'] = False

                logging.info("Dosificación de fertilizante completada.")
            else:
                logging.info("Porcentaje de fertilizante es 0%. No se realizará dosificación.")

            with self.lock:
                self.is_busy = False  # Finalizando acción crítica

        except Exception:
            logging.exception("Error al ajustar dosificación de fertilizante:")
            with self.lock:
                self.is_busy = False
            raise

    def _programar_riego_diario(self):
        """
        Programa los horarios de riego diarios basados en los requerimientos.
        """
        # Limpiar programación anterior
        for job in self.irrigation_schedule:
            schedule.cancel_job(job)
        self.irrigation_schedule.clear()

        # Definir horarios y días de riego
        irrigation_times = ['07:15', '08:15', '09:15']  # Horarios en los que se iniciará el riego
        irrigation_days = ['Monday', 'Tuesday', 'Wednesday']  # Días de la semana

        for day in irrigation_days:
            for irrigation_time in irrigation_times:
                # Ajustar el día específico
                job = getattr(schedule.every(), day.lower()).at(irrigation_time).do(self._iniciar_evento_riego)
                self.irrigation_schedule.append(job)

        logging.info(f"Horarios de riego programados: {irrigation_times} en días {irrigation_days}")

    def _iniciar_evento_riego(self):
        """
        Inicia un evento de riego, obteniendo nuevas predicciones antes de regar.
        """
        with self.lock:
            if self.remaining_daily_water <= 0:
                logging.info("No hay agua restante para distribuir en el riego de hoy.")
                return

        # Obtener los valores actuales de los sensores
        sensor_values = self._leer_sensores()

        # Obtener una nueva decisión del motor de decisiones
        decision = self.decision_engine.evaluar(sensor_values)

        # Actualizar la cantidad de agua y fertilizante para este evento
        cantidad_agua = decision.get('cantidad_agua', 0)
        porcentaje_fertilizante = decision.get('porcentaje_fertilizante', 0)

        with self.lock:
            # Verificar si hay suficiente agua restante
            if self.remaining_daily_water < cantidad_agua:
                cantidad_agua = self.remaining_daily_water

            # Actualizar agua restante
            self.remaining_daily_water -= cantidad_agua

        # Actualizar la decisión con la cantidad de agua ajustada
        decision['cantidad_agua'] = cantidad_agua
        decision['porcentaje_fertilizante'] = porcentaje_fertilizante

        # Iniciar el riego en un hilo separado para no bloquear el ciclo principal
        threading.Thread(target=self._controlar_riego, args=(decision,)).start()

    def _controlar_riego(self, decision):
        """
        Controla el riego asegurándose de suministrar la cantidad exacta de agua y fertilizante.
        """
        try:
            with self.lock:
                self.is_busy = True  # Iniciando acción crítica

            logging.info(f"Iniciando evento de riego con {decision['cantidad_agua']} litros de agua.")

            # Accionar los actuadores para el riego
            self._accionar_actuadores(decision)

            # Variables para monitorear el flujo
            total_volume = 0.0  # Volumen total suministrado en litros
            tiempo_inicio = time.time()
            tiempo_ultimo = tiempo_inicio

            # Tiempo máximo para prevenir riegos excesivamente largos (por ejemplo, 30 minutos)
            tiempo_maximo_riego = 1800  # 30 minutos

            while total_volume < decision['cantidad_agua']:
                # Leer el caudal actual en litros por minuto
                flow_rate = self.flow_sensor.leer()

                # Tiempo transcurrido desde la última lectura
                tiempo_actual = time.time()
                delta_tiempo = tiempo_actual - tiempo_ultimo

                # Calcular el volumen suministrado en este intervalo
                volumen_intervalo = (flow_rate / 60) * delta_tiempo  # Convertir L/min a L

                total_volume += volumen_intervalo
                tiempo_ultimo = tiempo_actual

                logging.debug(f"Caudal: {flow_rate:.2f} L/min, Volumen suministrado: {total_volume:.2f} L")

                # Esperar un breve periodo antes de la siguiente lectura
                time.sleep(1)

                # Verificar si se ha excedido el tiempo máximo de riego
                if (tiempo_actual - tiempo_inicio) > tiempo_maximo_riego:
                    logging.warning("Tiempo máximo de riego excedido. Deteniendo riego para prevenir sobreirrigación.")
                    break

            # Finalizar el riego
            self.pump_control.desactivar()
            self.valve_control.cerrar_valvula('valvula_riego')
            with self.lock:
                self.actuator_states['bomba'] = False
                self.actuator_states['valvula_riego'] = False

            logging.info(f"Evento de riego completado. Volumen total suministrado: {total_volume:.2f} litros.")

            # Registrar evento de riego
            self._registrar_evento_riego(tiempo_inicio, time.time(), total_volume)

            with self.lock:
                self.is_busy = False  # Finalizando acción crítica

        except Exception:
            logging.exception("Error durante el control del riego:")
            # Asegurarse de desactivar los actuadores en caso de error
            self.pump_control.desactivar()
            self.valve_control.cerrar_valvula('valvula_riego')
            with self.lock:
                self.actuator_states['bomba'] = False
                self.actuator_states['valvula_riego'] = False
                self.is_busy = False

    def _registrar_evento_riego(self, tiempo_inicio, tiempo_fin, total_volume):
        """
        Registra los detalles del evento de riego en un archivo CSV.
        """
        irrigation_events_file = 'data/irrigation_events.csv'
        file_exists = os.path.isfile(irrigation_events_file)

        evento = {
            'inicio': datetime.fromtimestamp(tiempo_inicio).strftime('%Y-%m-%d %H:%M:%S'),
            'fin': datetime.fromtimestamp(tiempo_fin).strftime('%Y-%m-%d %H:%M:%S'),
            'volumen': round(total_volume, 2)
        }

        campos = ['inicio', 'fin', 'volumen']

        try:
            with open(irrigation_events_file, mode='a', newline='') as archivo_csv:
                escritor = csv.DictWriter(archivo_csv, fieldnames=campos)
                if not file_exists:
                    escritor.writeheader()
                escritor.writerow(evento)
            logging.info("Evento de riego registrado en irrigation_events.csv.")
        except Exception:
            logging.exception("Error al registrar evento de riego:")

    def _monitorear_almacenamiento(self):
        """
        Monitorea la capacidad de la microSD y elimina datos antiguos si se supera el 80% de su capacidad.
        """
        try:
            total, used, free = shutil.disk_usage("/")
            used_percentage = (used / total) * 100

            if used_percentage >= 80:
                logging.warning("Capacidad de almacenamiento superior al 80%. Eliminando datos antiguos.")
                self._eliminar_datos_antiguos()
            else:
                logging.info(f"Capacidad de almacenamiento utilizada: {used_percentage:.2f}%")
        except Exception:
            logging.exception("Error al monitorear el almacenamiento:")

    def _eliminar_datos_antiguos(self):
        """
        Elimina los datos más antiguos para liberar espacio, manteniendo al menos 3 meses de datos.
        Antes de eliminar, realiza una copia de seguridad de los datos.
        """
        try:
            # Realizar copia de seguridad de datos
            self._backup_data_files()

            # Definir la ruta de los archivos de datos
            sensor_data_file = 'data/sensor_data.csv'
            decision_data_file = 'data/decision_data.csv'

            # Calcular la fecha límite (3 meses atrás)
            cutoff_date = datetime.now() - timedelta(days=90)

            # Función para filtrar y guardar datos recientes
            def filtrar_datos_recientes(file_path):
                if os.path.isfile(file_path):
                    df = pd.read_csv(file_path)
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df_recientes = df[df['timestamp'] >= cutoff_date]
                    df_recientes.to_csv(file_path, index=False)
                    logging.info(f"Datos antiguos eliminados en {file_path}")
                else:
                    logging.warning(f"Archivo no encontrado: {file_path}")

            # Filtrar datos en ambos archivos
            filtrar_datos_recientes(sensor_data_file)
            filtrar_datos_recientes(decision_data_file)

        except Exception:
            logging.exception("Error al eliminar datos antiguos:")

    def _backup_data_files(self):
        """
        Realiza una copia de seguridad de los archivos de datos antes de eliminar datos antiguos.
        """
        try:
            backup_dir = 'data/backup'
            os.makedirs(backup_dir, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

            files_to_backup = ['data/sensor_data.csv', 'data/decision_data.csv']
            for file_path in files_to_backup:
                if os.path.isfile(file_path):
                    backup_path = os.path.join(backup_dir, f"{os.path.basename(file_path)}_{timestamp}")
                    shutil.copy2(file_path, backup_path)
                    logging.info(f"Copia de seguridad creada: {backup_path}")
                else:
                    logging.warning(f"No se encontró el archivo para respaldar: {file_path}")
        except Exception:
            logging.exception("Error al realizar copia de seguridad de los datos:")

    def _programar_sincronizacion_semanal(self):
        """
        Programa la sincronización semanal con la nube en horario nocturno.
        """
        # Programar sincronización a las 2 AM si no está ocupado
        with self.lock:
            if not self.is_busy:
                schedule.every().week.do(self._sincronizar_con_nube).tag('sincronizacion_semanal')
                logging.info("Sincronización semanal programada a las 2 AM.")
            else:
                logging.warning("El sistema está ocupado. La sincronización semanal se reprogramará.")
                schedule.every(1).hours.do(self._programar_sincronizacion_semanal)

    def _sincronizar_con_nube(self):
        """
        Sincroniza los datos locales con la nube y actualiza el modelo de Machine Learning si hay
        una versión más reciente disponible en la nube.
        """
        try:
            with self.lock:
                if self.is_busy:
                    logging.warning("El sistema está ocupado. Posponiendo sincronización con la nube.")
                    return

            # Realizar sincronización completa con la nube
            sincronizacion_exitosa = self.cloud_sync.sincronizar_con_nube()

            if sincronizacion_exitosa:
                # Cargar el modelo actualizado en el decision_engine
                self.decision_engine.cargar_modelo()
                logging.info("Modelo de Machine Learning actualizado desde la nube.")
            else:
                logging.warning("La sincronización con la nube no fue exitosa. Se mantendrá el modelo anterior.")

        except Exception:
            logging.exception("Error en sincronización con la nube:")

    def _guardar_decision_csv(self, sensor_values, decision):
        """
        Guarda las decisiones tomadas junto con los datos de sensores en un archivo CSV.
        """
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
        campos = ['timestamp', 'humidity', 'temperature', 'ph', 'ce', 'water_level', 'flow_rate', 'season',
                  'activar_bomba', 'abrir_valvula_riego', 'inyectar_fertilizante', 'abrir_valvula_suministro',
                  'porcentaje_fertilizante', 'cantidad_agua']

        # Asegurarse de que todos los campos de actuadores están presentes
        for key in ['activar_bomba', 'abrir_valvula_riego', 'inyectar_fertilizante', 'abrir_valvula_suministro']:
            if key not in data_csv or data_csv[key] is None:
                data_csv[key] = False

        # Asegurarse de que 'water_level' está presente
        if 'water_level' not in data_csv:
            data_csv['water_level'] = None

        # Asegurarse de que 'porcentaje_fertilizante' y 'cantidad_agua' están presentes
        if 'porcentaje_fertilizante' not in data_csv:
            data_csv['porcentaje_fertilizante'] = 0
        if 'cantidad_agua' not in data_csv:
            data_csv['cantidad_agua'] = 0

        try:
            # Escribir en el CSV usando data_csv
            with open(decision_csv, mode='a', newline='') as archivo_csv:
                escritor = csv.DictWriter(archivo_csv, fieldnames=campos)
                if not file_exists:
                    escritor.writeheader()
                escritor.writerow(data_csv)

            logging.info("Decisión guardada en decision_data.csv.")

        except Exception:
            logging.exception("Error al guardar decisión en CSV:")
            raise
