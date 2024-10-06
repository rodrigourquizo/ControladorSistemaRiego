# sensors.py

import time
import logging
import threading
import random
import sys
# Importar librerías necesarias para Modbus RTU sobre RS485
try:
    from pymodbus.client import ModbusSerialClient
    from pymodbus.constants import Endian
    from pymodbus.payload import BinaryPayloadDecoder
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
    # Pines de alimentación para sensores y conversor
    GPIO.setup(4, GPIO.OUT)   # VCC
    GPIO.setup(6, GPIO.OUT)   # GND

    # Pines para RS485 (MAX485 o similar)
    GPIO.setup(14, GPIO.OUT)  # DE (Driver Enable)
    GPIO.setup(15, GPIO.IN)   # RE (Receiver Enable)
    GPIO.setup(27, GPIO.OUT)  # Control de DE/RE

    # Pines para sensor de flujo
    GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # GPIO 17 - Salida de pulsos del sensor de flujo

    # Pines para sensor US-100
    GPIO.setup(18, GPIO.OUT)  # TRIG/TX del sensor US-100
    GPIO.setup(24, GPIO.IN)   # ECHO/RX del sensor US-100

    # Configurar pines de alimentación
    GPIO.output(4, GPIO.HIGH)  # Activar VCC
    GPIO.output(6, GPIO.LOW)   # Conectar GND

    # Configurar control DE/RE en recepción inicialmente
    GPIO.setup(27, GPIO.OUT)
    GPIO.output(27, GPIO.LOW)  # RE y DE en bajo para recepción

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
            # Configurar pines para RS485
            cls.DE_RE_PIN = 27  # GPIO 27 para DE y RE del MAX485
            serial_port = '/dev/ttyS0'  # Puerto serial para Raspberry Pi (UART)
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
                    # Controlar DE/RE para transmisión
                    GPIO.output(self.DE_RE_PIN, GPIO.HIGH)  # Modo transmisión
                    time.sleep(0.01)  # Pequeña espera para cambio de modo
                    result = self.modbus_client.read_holding_registers(register_address, register_count, unit=self.address)
                    GPIO.output(self.DE_RE_PIN, GPIO.LOW)  # Modo recepción
                if not result.isError():
                    logging.debug(f"Lectura Modbus desde dirección {self.address}: {result.registers}")
                    return result.registers
                else:
                    logging.error(f"Error al leer Modbus en dirección {self.address}: {result}")
                    raise Exception("Error al leer Modbus")
            except Exception as e:
                logging.error(f"Error al leer Modbus en dirección {self.address}: {e}")
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
        raw_value = self.leer_modbus(self.register_address, self.register_count)
        calibrated_value = self.calibrar(raw_value)
        self.last_reading = calibrated_value
        return calibrated_value

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

                self.last_reading = {
                    'humidity': humidity,
                    'temperature': temperature,
                    'ce': ce,
                    'ph': ph
                }

                logging.debug(f"Valores calibrados: {self.last_reading}")
                return self.last_reading
            else:
                logging.error("No se pudieron obtener los valores del sensor de suelo.")
                return None
        else:
            # Modo simulado
            self.last_reading = {
                'humidity': random.uniform(0, 100),
                'temperature': random.uniform(-20, 80),
                'ce': random.uniform(0, 20000),
                'ph': random.uniform(3, 9)
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

        if not self.simulation_mode:
            GPIO.setup(self.trig_pin, GPIO.OUT)
            GPIO.setup(self.echo_pin, GPIO.IN)
            logging.info("Sensor de Nivel de Agua inicializado.")
        else:
            logging.info("Sensor de Nivel de Agua inicializado en modo simulado.")

    def leer(self):
        """
        Lee la distancia medida por el sensor ultrasonido y calcula el nivel de agua.
        """
        if not self.simulation_mode:
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

            # Calcular nivel de agua en porcentaje
            tank_height = self.calibration_params.get('tank_height', 200)  # Altura del tanque en cm
            nivel = ((tank_height - distancia) / tank_height) * 100
            nivel = max(0, min(100, nivel))  # Limitar entre 0% y 100%
            self.last_reading = nivel
            logging.debug(f"Nivel de agua medido: {nivel:.2f}%")
            return nivel
        else:
            # Modo simulado
            nivel = random.uniform(0, 100)
            self.last_reading = nivel
            logging.debug(f"Nivel de agua simulado: {nivel:.2f}%")
            return nivel

class FlowSensor:
    """
    Sensor de flujo de agua FS300A
    """
    def __init__(self, gpio_pin, calibration_params=None):
        self.gpio_pin = gpio_pin
        self.calibration_params = calibration_params or {}
        self.last_reading = None
        self.simulation_mode = sys.platform == "win32"
        self.flow_frequency = 0
        self.conversion_factor = self.calibration_params.get('factor', 5.5)

        if not self.simulation_mode:
            GPIO.setup(self.gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.add_event_detect(self.gpio_pin, GPIO.RISING, callback=self._count_pulse)
            logging.info("Sensor de flujo inicializado.")
        else:
            logging.info("Sensor de flujo inicializado en modo simulado.")

    def _count_pulse(self, channel):
        self.flow_frequency += 1

    def leer(self):
        """
        Lee el caudal actual en litros por minuto.
        """
        if not self.simulation_mode:
            # Medir el número de pulsos durante 1 segundo
            self.flow_frequency = 0
            time.sleep(1)
            frequency = self.flow_frequency  # Pulsos por segundo (Hz)
            # Calcular el caudal en L/min
            flow_rate = frequency / self.conversion_factor
            self.last_reading = flow_rate
            logging.debug(f"Caudal medido: {flow_rate:.3f} L/min")
            return flow_rate
        else:
            # Modo simulado
            flow_rate = random.uniform(0, 60)  # Rango del sensor 1-60 L/min
            self.last_reading = flow_rate
            logging.debug(f"Caudal simulado: {flow_rate:.3f} L/min")
            return flow_rate

    def detectar_fallo(self, expected_flow):
        """
        Detecta si hay fuga o bloqueo en las tuberías.
        :param expected_flow: Caudal esperado en L/min
        :return: True si hay fallo, False si todo está bien
        """
        if self.last_reading is None:
            logging.warning("No se ha podido obtener lectura del sensor de flujo.")
            return True
        if expected_flow is not None:
            # Definir tolerancia para detectar anomalías
            tolerance = self.calibration_params.get('tolerance', 0.2)  # 20% de tolerancia
            if self.last_reading < expected_flow * (1 - tolerance):
                logging.error("Posible bloqueo en las tuberías detectado.")
                return True
            elif self.last_reading > expected_flow * (1 + tolerance):
                logging.error("Posible fuga en las tuberías detectada.")
                return True
        return False
