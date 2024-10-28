# sensors.py

import time
import logging
import threading
import random
import sys

# Importar librerías necesarias para Modbus RTU sobre RS485
try:
    from pymodbus.client import ModbusSerialClient
except ImportError:
    logging.warning("Librería pymodbus no disponible. Ejecutando en modo simulado.")
    ModbusSerialClient = None

# Simular RPi.GPIO solo si no estamos en una Raspberry Pi
if sys.platform == "win32":
    from unittest.mock import MagicMock
    GPIO = MagicMock()
    logging.warning("Librerías de hardware no disponibles. Ejecutando en modo simulado.")
else:
    try:
        import RPi.GPIO as GPIO
    except ImportError:
        logging.warning("Librerías de RPi.GPIO no disponibles en este entorno.")
        GPIO = None

# Configuración del logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# Configurar GPIO
if GPIO is not None:
    GPIO.setmode(GPIO.BCM)

    # Pines para RS485 (MAX485 o similar)
    DE_RE_PIN = 27  # GPIO 27 para DE y RE del MAX485

    # Pines para sensor de flujo
    FLOW_SENSOR_PIN = 17  # GPIO 17 - Salida de pulsos del sensor de flujo

    # Pines para sensor US-100
    TRIG_PIN = 18  # TRIG del sensor US-100
    ECHO_PIN = 24  # ECHO del sensor US-100

    # Configurar pines de alimentación si es necesario
    # NOTA: No se recomienda usar GPIO para alimentación de sensores

class SensorBase:
    """
    Clase base para los sensores Modbus.
    """
    modbus_client = None
    modbus_lock = threading.Lock()

    @classmethod
    def initialize_modbus_client(cls):
        if cls.modbus_client is None:
            if not GPIO:
                logging.error("GPIO no está disponible. No se puede inicializar Modbus.")
                return
            # Configurar el cliente Modbus RTU
            serial_port = '/dev/ttyS0'  # Ajustar según la configuración de la Raspberry Pi
            cls.modbus_client = ModbusSerialClient(
                method='rtu',
                port=serial_port,
                baudrate=9600,
                bytesize=8,
                parity='N',
                stopbits=1,
                timeout=1,
            )
            if cls.modbus_client.connect():
                logging.info("Cliente Modbus conectado exitosamente.")
            else:
                logging.error("Fallo al conectar el cliente Modbus.")

    def __init__(self, address, calibration_params=None):
        """
        Inicializa el sensor con la dirección Modbus y parámetros de calibración.
        """
        self.address = address  # ID del esclavo Modbus
        self.calibration_params = calibration_params or {}
        self.last_reading = None
        self.simulation_mode = sys.platform == "win32"

        # Implementación de lock para seguridad de hilos
        self.lock = threading.Lock()

        if not self.simulation_mode:
            self.initialize_modbus_client()
        else:
            logging.info(f"Sensor en dirección {self.address} inicializado en modo simulado.")

    def leer_modbus(self, register_address, register_count):
        """
        Lee los registros Modbus del sensor.
        """
        if not self.simulation_mode and self.modbus_client:
            try:
                with self.modbus_lock:
                    # Controlar DE/RE para transmisión y recepción
                    GPIO.output(DE_RE_PIN, GPIO.HIGH)  # Modo transmisión
                    time.sleep(0.01)  # Pequeña espera para cambio de modo
                    result = self.modbus_client.read_holding_registers(
                        address=register_address,
                        count=register_count,
                        unit=self.address
                    )
                    GPIO.output(DE_RE_PIN, GPIO.LOW)  # Modo recepción
                if not result.isError():
                    logging.debug(f"Lectura Modbus desde dirección {self.address}: {result.registers}")
                    return result.registers
                else:
                    logging.error(f"Error al leer Modbus en dirección {self.address}: {result}")
                    raise IOError("Error al leer Modbus")
            except Exception:
                logging.exception(f"Error al leer Modbus en dirección {self.address}:")
                raise
        else:
            # Modo simulado
            return [random.randint(0, 1000) for _ in range(register_count)]

    def calibrar(self, raw_value):
        """
        Aplica la calibración al valor bruto leído vía Modbus.
        Este método debe ser implementado por cada sensor específico.
        """
        raise NotImplementedError("El método calibrar() debe ser implementado por subclases.")

    def leer(self):
        """
        Lee el valor del sensor, aplica calibración y detecta posibles fallos.
        :return: Valor calibrado del sensor.
        """
        raise NotImplementedError("El método leer() debe ser implementado por las subclases.")

    def detectar_fallo(self):
        """
        Implementa la lógica para detectar fallos en el sensor.
        """
        pass

class SoilSensor(SensorBase):
    """
    Sensor 4 en 1 RS485 que mide temperatura, humedad, CE y pH.
    """
    def __init__(self, address, calibration_params=None):
        super().__init__(address, calibration_params)
        self.register_address = 0x0000  # Dirección inicial del registro
        self.register_count = 4         # Cantidad de registros a leer (humedad, temperatura, CE, pH)
        logging.info("Sensor de Suelo 4 en 1 inicializado.")

    def leer(self):
        """
        Lee todos los valores del sensor y los calibra.
        :return: Diccionario con humedad, temperatura, CE y pH.
        """
        if not self.simulation_mode:
            try:
                raw_values = self.leer_modbus(self.register_address, self.register_count)
                if raw_values:
                    humidity_raw = raw_values[0]
                    temperature_raw = raw_values[1]
                    ce_raw = raw_values[2]
                    ph_raw = raw_values[3]

                    humidity = humidity_raw / 10.0  # Humedad en %
                    temperature = self._calibrar_temperatura(temperature_raw)  # Temperatura en °C
                    ce = ce_raw  # CE en μS/cm
                    ph = ph_raw / 10.0  # pH

                    with self.lock:
                        self.last_reading = {
                            'humidity': humidity,
                            'temperature': temperature,
                            'ce': ce,
                            'ph': ph
                        }

                    logging.debug(f"Valores calibrados: {self.last_reading}")

                    # Detectar fallos
                    if self.detectar_fallo():
                        return None

                    return self.last_reading
                else:
                    logging.error("No se pudieron obtener los valores del sensor de suelo.")
                    return None
            except Exception:
                logging.exception("Error al leer el sensor de suelo:")
                return None
        else:
            # Modo simulado con valores realistas
            with self.lock:
                self.last_reading = {
                    'humidity': random.uniform(30, 70),
                    'temperature': random.uniform(10, 30),
                    'ce': random.uniform(1.0, 2.5),
                    'ph': random.uniform(5.5, 7.5)
                }
            logging.debug(f"Valores simulados: {self.last_reading}")
            return self.last_reading

    def _calibrar_temperatura(self, raw_value):
        """
        Calibra el valor de temperatura, considerando números negativos.
        """
        if raw_value >= 0x8000:
            # Número negativo en complemento a dos
            temperature = -(0x10000 - raw_value) / 10.0
        else:
            temperature = raw_value / 10.0
        return temperature

    def detectar_fallo(self):
        """
        Verifica si los valores leídos están dentro de rangos aceptables.
        """
        with self.lock:
            if self.last_reading is None:
                logging.error("No hay lectura disponible del sensor de suelo.")
                return True
            # Verificar valores fuera de rango
            if not (0 <= self.last_reading['humidity'] <= 100):
                logging.error(f"Lectura de humedad fuera de rango: {self.last_reading['humidity']}")
                return True
            if not (-40 <= self.last_reading['temperature'] <= 80):
                logging.error(f"Lectura de temperatura fuera de rango: {self.last_reading['temperature']}")
                return True
            if not (0 <= self.last_reading['ce'] <= 2000):
                logging.error(f"Lectura de CE fuera de rango: {self.last_reading['ce']}")
                return True
            if not (3 <= self.last_reading['ph'] <= 9):
                logging.error(f"Lectura de pH fuera de rango: {self.last_reading['ph']}")
                return True
        return False

class LevelSensor:
    """
    Sensor de nivel de agua US-100 en modo Trigger/Echo.
    """
    def __init__(self, trig_pin, echo_pin, calibration_params=None):
        self.trig_pin = trig_pin
        self.echo_pin = echo_pin
        self.calibration_params = calibration_params or {}
        self.last_reading = None
        self.simulation_mode = sys.platform == "win32"
        self.simulated_water_level = 79.0  # Nivel inicial en porcentaje
        # Implementación de lock para seguridad de hilos
        self.lock = threading.Lock()

        if not self.simulation_mode:
            GPIO.setup(self.trig_pin, GPIO.OUT)
            GPIO.setup(self.echo_pin, GPIO.IN)
            logging.info("Sensor de Nivel de Agua inicializado.")
        else:
            logging.info("Sensor de Nivel de Agua inicializado en modo simulado.")

    def leer(self, bomba_activa=False, num_samples=5):
        """
        Lee la distancia medida por el sensor ultrasonido y calcula el nivel de agua.
        Toma múltiples muestras y calcula un promedio para reducir el ruido.
        """
        if not self.simulation_mode:
            try:
                distances = []
                for _ in range(num_samples):
                    distance = self._medir_distancia()
                    if distance is not None:
                        distances.append(distance)
                    time.sleep(0.1)  # Pequeña espera entre lecturas

                if distances:
                    average_distance = sum(distances) / len(distances)
                    # Calcular nivel de agua en porcentaje
                    tank_height = self.calibration_params.get('tank_height', 80)  # Altura del tanque en cm
                    nivel = ((tank_height - average_distance) / tank_height) * 100
                    nivel = max(0, min(100, nivel))  # Limitar entre 0% y 100%
                    with self.lock:
                        self.last_reading = nivel

                    logging.debug(f"Nivel de agua medido: {nivel:.2f}%")

                    # Detectar fallos
                    if self.detectar_fallo():
                        return None

                    return nivel
                else:
                    logging.error("No se pudo leer distancia del sensor ultrasónico.")
                    return None
            except Exception:
                logging.exception("Error al leer el sensor de nivel de agua:")
                return None
        else:
            with self.lock:
                if bomba_activa:
                    # Disminuir el nivel de agua simulando el consumo
                    decrement = 0.5  # Decremento por lectura
                    self.simulated_water_level = max(self.simulated_water_level - decrement, 0.0)
                else:
                    # Recuperación lenta del nivel (por ejemplo, por lluvia)
                    increment = 0.1  # Incremento por lectura
                    self.simulated_water_level = min(self.simulated_water_level + increment, 100.0)

                nivel = self.simulated_water_level
                self.last_reading = nivel

            logging.debug(f"Nivel de agua simulado: {nivel:.2f}%")
            return nivel

    def _medir_distancia(self):
        """
        Realiza una medición de distancia con el sensor ultrasónico.
        """
        try:
            # Asegurarse de que el pin TRIG está bajo
            GPIO.output(self.trig_pin, False)
            time.sleep(0.0002)

            # Enviar un pulso de 10μs en el pin TRIG
            GPIO.output(self.trig_pin, True)
            time.sleep(0.00001)
            GPIO.output(self.trig_pin, False)

            # Medir el tiempo de respuesta del eco
            timeout = time.time() + 1  # Timeout de 1 segundo

            while GPIO.input(self.echo_pin) == 0:
                inicio_pulso = time.time()
                if inicio_pulso > timeout:
                    logging.error("Timeout esperando inicio del pulso ECHO")
                    return None

            while GPIO.input(self.echo_pin) == 1:
                fin_pulso = time.time()
                if fin_pulso > timeout:
                    logging.error("Timeout esperando fin del pulso ECHO")
                    return None

            duracion_pulso = fin_pulso - inicio_pulso

            # Calcular la distancia (velocidad del sonido 34300 cm/s)
            distancia = (duracion_pulso * 34300) / 2  # En cm

            return distancia
        except Exception:
            logging.exception("Error al medir distancia con el sensor ultrasónico:")
            return None

    def detectar_fallo(self, expected_flow=None):
        """
        Detecta si hay fuga o bloqueo en las tuberías.
        :param expected_flow: Caudal esperado en L/min
        :return: True si hay fallo, False si todo está bien
        """
        with self.lock:
            if self.last_reading is None:
                logging.warning("No se ha podido obtener lectura del sensor de flujo.")
                return True
            if expected_flow is not None:
                # Definir tolerancia para detectar anomalías
                tolerance = self.calibration_params.get('tolerance', 0.2)  # 20% de tolerancia
                if expected_flow == 0:
                    # No se espera flujo; si hay flujo significativo, podría ser una fuga
                    if self.last_reading > 0.5:  # Umbral mínimo para evitar ruido
                        logging.error("Posible fuga en las tuberías detectada. Flujo detectado cuando no debería haber.")
                        return True
                else:
                    # Se espera flujo; verificar desviaciones
                    if self.last_reading < expected_flow * (1 - tolerance):
                        logging.error("Posible bloqueo en las tuberías detectado.")
                        return True
                    elif self.last_reading > expected_flow * (1 + tolerance):
                        logging.error("Posible fuga en las tuberías detectada.")
                        return True
        return False

class FlowSensor:
    """
    Sensor de flujo de agua FS300A.
    """
    def __init__(self, gpio_pin, calibration_params=None):
        self.gpio_pin = gpio_pin
        self.calibration_params = calibration_params or {}
        self.last_reading = None
        self.simulation_mode = sys.platform == "win32"
        self.flow_frequency = 0
        self.conversion_factor = self.calibration_params.get('factor', 5.5)
        self.counting_event = threading.Event()
        self.simulated_flow_rate = 0.0  # Añadido para simular el flujo actual
        # Implementación de lock para seguridad de hilos
        self.lock = threading.Lock()

        if not self.simulation_mode:
            GPIO.setup(self.gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.add_event_detect(self.gpio_pin, GPIO.RISING, callback=self._count_pulse)
            logging.info("Sensor de flujo inicializado.")
        else:
            logging.info("Sensor de flujo inicializado en modo simulado.")

    def _count_pulse(self, channel):
        with self.lock:
            self.flow_frequency += 1

    def leer(self, bomba_activa=False, valvula_riego_abierta=False):
        """
        Lee el caudal actual en litros por minuto.
        :param bomba_activa: Estado de la bomba (True si está activa)
        :param valvula_riego_abierta: Estado de la válvula de riego (True si está abierta)
        :return: Caudal en L/min
        """
        if not self.simulation_mode:
            try:
                # Reiniciar contador
                with self.lock:
                    self.flow_frequency = 0
                # Esperar durante 1 segundo sin bloquear el hilo principal
                time.sleep(1)
                # Obtener frecuencia
                with self.lock:
                    frequency = self.flow_frequency
                # Calcular el caudal en L/min
                flow_rate = (frequency / self.conversion_factor)
                with self.lock:
                    self.last_reading = flow_rate

                logging.debug(f"Caudal medido: {flow_rate:.3f} L/min")

                # Detectar fallos
                if self.detectar_fallo():
                    return None

                return flow_rate
            except Exception:
                logging.exception("Error al leer el sensor de flujo:")
                return None
        else:
            # Modo simulado con lógica mejorada
            with self.lock:
                if bomba_activa and valvula_riego_abierta:
                    # Incrementar gradualmente el flujo hasta un máximo
                    max_flow_rate = 60.0  # Máximo caudal en L/min
                    increment = 5.0        # Incremento por lectura
                    self.simulated_flow_rate = min(self.simulated_flow_rate + increment, max_flow_rate)
                else:
                    # Decrementar gradualmente el flujo hasta llegar a cero
                    decrement = 5.0  # Decremento por lectura
                    self.simulated_flow_rate = max(self.simulated_flow_rate - decrement, 0.0)

                flow_rate = self.simulated_flow_rate
                self.last_reading = flow_rate

            logging.debug(f"Caudal simulado: {flow_rate:.3f} L/min")
            return flow_rate

    def detectar_fallo(self, expected_flow=None):
        """
        Detecta si hay fuga o bloqueo en las tuberías.
        :param expected_flow: Caudal esperado en L/min
        :return: True si hay fallo, False si todo está bien
        """
        with self.lock:
            if self.last_reading is None:
                logging.warning("No se ha podido obtener lectura del sensor de flujo.")
                return True
            if expected_flow is not None:
                # Definir tolerancia para detectar anomalías
                tolerance = self.calibration_params.get('tolerance', 0.2)  # 20% de tolerancia
                minimal_flow_threshold = self.calibration_params.get('minimal_flow_threshold', 0.5)  # Umbral mínimo para considerar flujo significativo

                if expected_flow == 0:
                    # No se espera flujo; si hay flujo significativo, podría ser una fuga
                    if self.last_reading > minimal_flow_threshold:
                        logging.error("Posible fuga en las tuberías detectada. Flujo detectado cuando no debería haber.")
                        return True
                else:
                    # Se espera flujo; verificar desviaciones
                    if self.last_reading < expected_flow * (1 - tolerance):
                        logging.error("Posible bloqueo en las tuberías detectado.")
                        return True
                    elif self.last_reading > expected_flow * (1 + tolerance):
                        logging.error("Posible fuga en las tuberías detectada.")
                        return True
        return False