import time
import logging
import threading
import random
import sys
from unittest.mock import MagicMock
# Importar librerías necesarias para interactuar con el hardware
try:
    import Adafruit_ADS1x15  # Librería para el ADC ADS1115
except ImportError:
    logging.warning("Librería Adafruit_ADS1x15 no disponible. Ejecutando en modo simulado.")
    Adafruit_ADS1x15 = None

# Simular RPi.GPIO solo si no estamos en un Raspberry Pi
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


class SensorBase:
    """
    Clase base para los sensores. Proporciona métodos comunes como lectura del ADC,
    calibración y detección de fallos.
    """
    def __init__(self, channel, adc_gain=1, calibration_params=None):
        """
        Inicializa el sensor con el canal ADC correspondiente y parámetros de calibración.

        :param channel: Canal del ADC al que está conectado el sensor (0-3).
        :param adc_gain: Ganancia del ADC (por defecto 1).
        :param calibration_params: Parámetros de calibración específicos del sensor.
        """
        self.channel = channel
        self.adc_gain = adc_gain
        self.calibration_params = calibration_params or {}
        self.last_reading = None
        self.adc = None
        self.simulation_mode = sys.platform == "win32"

        if Adafruit_ADS1x15 is not None and not self.simulation_mode:
            try:
                self.adc = Adafruit_ADS1x15.ADS1115()
                logging.info(f"Sensor en canal {self.channel} inicializado con hardware real.")
            except Exception as e:
                logging.warning(f"No se pudo inicializar el ADC: {e}. Ejecutando en modo simulado.")
                self.adc = None
        else:
            logging.info(f"Sensor en canal {self.channel} inicializado en modo simulado.")

    def leer_adc(self):
        """
        Lee el valor bruto del ADC para el canal especificado.
        :return: Valor entero leído del ADC.
        """
        if self.adc:
            try:
                value = self.adc.read_adc(self.channel, gain=self.adc_gain)
                logging.debug(f"Valor bruto del ADC en canal {self.channel}: {value}")
                return value
            except Exception as e:
                logging.error(f"Error al leer el ADC en canal {self.channel}: {e}")
                raise
        else:
            # Modo simulado, implementado en cada sensor específico
            raise NotImplementedError("La lectura simulada del ADC debe ser implementada en cada sensor.")

    def calibrar(self, raw_value):
        """
        Aplica la calibración al valor bruto leído del ADC.
        Este método debe ser implementado por cada sensor específico.
        """
        raise NotImplementedError("El método calibrar() debe ser implementado por subclases.")

    def leer(self):
        """
        Lee el valor del sensor, aplica calibración y detecta posibles fallos.
        :return: Valor calibrado del sensor.
        """
        raw_value = self.leer_adc()
        calibrated_value = self.calibrar(raw_value)
        self.last_reading = calibrated_value
        return calibrated_value

    def detectar_fallo(self):
        """
        Implementa la lógica para detectar fallos en el sensor.
        """
        pass

    def iniciar_monitoreo(self):
        """
        Inicia un hilo separado para monitorear el sensor en busca de fallos.
        """
        threading.Thread(target=self._monitorear_sensor).start()

    def _monitorear_sensor(self):
        """
        Hilo que monitorea continuamente el sensor para detectar fallos.
        """
        while True:
            try:
                self.detectar_fallo()
                time.sleep(60)  # Verificar cada minuto
            except Exception as e:
                logging.error(f"Error en monitoreo del sensor en canal {self.channel}: {e}")
                break


class HumiditySensor(SensorBase):
    """
    Sensor de humedad del suelo.
    """
    def __init__(self, channel, adc_gain=1, calibration_params=None):
        super().__init__(channel, adc_gain, calibration_params)
        logging.info("Sensor de Humedad inicializado.")

    def leer_adc(self):
        if self.adc:
            # Lectura del hardware
            try:
                value = self.adc.read_adc(self.channel, gain=self.adc_gain)
                logging.debug(f"Valor bruto del ADC en canal {self.channel}: {value}")
                return value
            except Exception as e:
                logging.error(f"Error al leer el ADC en canal {self.channel}: {e}")
                raise
        else:
            # Modo simulado
            try:
                min_adc = int(float(self.calibration_params.get('min_adc', 0)))
                max_adc = int(float(self.calibration_params.get('max_adc', 32767)))
                logging.debug(f"min_adc: {min_adc}, max_adc: {max_adc}")
            except (TypeError, ValueError) as e:
                logging.error(f"Error en 'min_adc' o 'max_adc' en HumiditySensor: {e}")
                min_adc = 0
                max_adc = 32767
            value = random.randint(min_adc, max_adc)
            logging.debug(f"Valor simulado del ADC de humedad en canal {self.channel}: {value}")
            return value

    def calibrar(self, raw_value):
        """
        Convierte el valor bruto del ADC en porcentaje de humedad.
        """
        try:
            min_adc = float(self.calibration_params.get('min_adc', 0))
            max_adc = float(self.calibration_params.get('max_adc', 32767))
            min_humidity = float(self.calibration_params.get('min_humidity', 0.0))
            max_humidity = float(self.calibration_params.get('max_humidity', 100.0))
            logging.debug(f"Calibración de humedad: min_adc={min_adc}, max_adc={max_adc}, min_humidity={min_humidity}, max_humidity={max_humidity}")
        except (TypeError, ValueError) as e:
            logging.error(f"Error en parámetros de calibración en HumiditySensor: {e}")
            min_adc, max_adc = 0, 32767
            min_humidity, max_humidity = 0.0, 100.0

        if max_adc != min_adc:
            humidity = (raw_value - min_adc) * (max_humidity - min_humidity) / (max_adc - min_adc) + min_humidity
        else:
            logging.error("max_adc y min_adc son iguales, división por cero en calibración.")
            humidity = min_humidity
        humidity = max(min(humidity, max_humidity), min_humidity)
        logging.debug(f"Valor de humedad calibrado: {humidity:.2f}%")
        return humidity

    def detectar_fallo(self):
        """
        Detecta si el sensor de humedad está fallando.
        """
        if self.last_reading is None:
            logging.warning("No se ha podido obtener lectura del sensor de humedad.")
            return True
        return False


class PhSensor(SensorBase):
    """
    Sensor de pH.
    """
    def __init__(self, channel, adc_gain=1, calibration_params=None):
        super().__init__(channel, adc_gain, calibration_params)
        logging.info("Sensor de pH inicializado.")

    def leer_adc(self):
        if self.adc:
            # Lectura del hardware
            try:
                value = self.adc.read_adc(self.channel, gain=self.adc_gain)
                logging.debug(f"Valor bruto del ADC en canal {self.channel}: {value}")
                return value
            except Exception as e:
                logging.error(f"Error al leer el ADC en canal {self.channel}: {e}")
                raise
        else:
            # Modo simulado
            try:
                min_adc = int(float(self.calibration_params.get('min_adc', 0)))
                max_adc = int(float(self.calibration_params.get('max_adc', 32767)))
                logging.debug(f"min_adc: {min_adc}, max_adc: {max_adc}")
            except (TypeError, ValueError) as e:
                logging.error(f"Error en 'min_adc' o 'max_adc' en PhSensor: {e}")
                min_adc = 0
                max_adc = 32767
            value = random.randint(min_adc, max_adc)
            logging.debug(f"Valor simulado del ADC de pH en canal {self.channel}: {value}")
            return value

    def calibrar(self, raw_value):
        """
        Convierte el valor bruto del ADC en valor de pH.
        """
        try:
            min_adc = float(self.calibration_params.get('min_adc', 0))
            max_adc = float(self.calibration_params.get('max_adc', 32767))
            min_ph = float(self.calibration_params.get('min_ph', 0.0))
            max_ph = float(self.calibration_params.get('max_ph', 14.0))
            logging.debug(f"Calibración lineal de pH: min_adc={min_adc}, max_adc={max_adc}, min_ph={min_ph}, max_ph={max_ph}")
            if max_adc != min_adc:
                ph = (raw_value - min_adc) * (max_ph - min_ph) / (max_adc - min_adc) + min_ph
            else:
                logging.error("max_adc y min_adc son iguales, división por cero en calibración.")
                ph = min_ph
        except (TypeError, ValueError) as e:
            logging.error(f"Error en parámetros de calibración en PhSensor: {e}")
            ph = 7.0  # Valor por defecto
        ph = max(min(ph, 14.0), 0.0)
        logging.debug(f"Valor de pH calibrado: {ph:.2f}")
        return ph

    def detectar_fallo(self):
        """
        Detecta si el sensor de pH está fallando.
        """
        if self.last_reading is None:
            logging.warning("No se ha podido obtener lectura del sensor de pH.")
            return True
        return False


class CESensor(SensorBase):
    """
    Sensor de Conductividad Eléctrica (CE).
    """
    def __init__(self, channel, adc_gain=1, calibration_params=None):
        super().__init__(channel, adc_gain, calibration_params)
        logging.info("Sensor de Conductividad Eléctrica inicializado.")

    def leer_adc(self):
        if self.adc:
            # Lectura del hardware
            try:
                value = self.adc.read_adc(self.channel, gain=self.adc_gain)
                logging.debug(f"Valor bruto del ADC en canal {self.channel}: {value}")
                return value
            except Exception as e:
                logging.error(f"Error al leer el ADC en canal {self.channel}: {e}")
                raise
        else:
            # Modo simulado
            try:
                min_adc = int(float(self.calibration_params.get('min_adc', 0)))
                max_adc = int(float(self.calibration_params.get('max_adc', 32767)))
                logging.debug(f"min_adc: {min_adc}, max_adc: {max_adc}")
            except (TypeError, ValueError) as e:
                logging.error(f"Error en 'min_adc' o 'max_adc' en CESensor: {e}")
                min_adc = 0
                max_adc = 32767
            value = random.randint(min_adc, max_adc)
            logging.debug(f"Valor simulado del ADC de CE en canal {self.channel}: {value}")
            return value

    def calibrar(self, raw_value):
        """
        Convierte el valor bruto del ADC en valor de CE (mS/cm).
        """
        try:
            min_adc = float(self.calibration_params.get('min_adc', 0))
            max_adc = float(self.calibration_params.get('max_adc', 32767))
            min_ce = float(self.calibration_params.get('min_ce', 0.0))
            max_ce = float(self.calibration_params.get('max_ce', 5.0))
            logging.debug(f"Calibración de CE: min_adc={min_adc}, max_adc={max_adc}, min_ce={min_ce}, max_ce={max_ce}")
        except (TypeError, ValueError) as e:
            logging.error(f"Error en parámetros de calibración en CESensor: {e}")
            min_adc, max_adc = 0, 32767
            min_ce, max_ce = 0.0, 5.0

        if max_adc != min_adc:
            ce = (raw_value - min_adc) * (max_ce - min_ce) / (max_adc - min_adc) + min_ce
        else:
            logging.error("max_adc y min_adc son iguales, división por cero en calibración.")
            ce = min_ce
        ce = max(min(ce, max_ce), min_ce)
        logging.debug(f"Valor de CE calibrado: {ce:.2f} mS/cm")
        return ce

    def detectar_fallo(self):
        """
        Detecta si el sensor de CE está fallando.
        """
        if self.last_reading is None:
            logging.warning("No se ha podido obtener lectura del sensor de CE.")
            return True
        return False


class LevelSensor(SensorBase):
    """
    Sensor de nivel de agua.
    """
    def __init__(self, channel, adc_gain=1, calibration_params=None):
        super().__init__(channel, adc_gain, calibration_params)
        logging.info("Sensor de Nivel de Agua inicializado.")

    def leer_adc(self):
        if self.adc:
            # Lectura del hardware
            try:
                value = self.adc.read_adc(self.channel, gain=self.adc_gain)
                logging.debug(f"Valor bruto del ADC en canal {self.channel}: {value}")
                return value
            except Exception as e:
                logging.error(f"Error al leer el ADC en canal {self.channel}: {e}")
                raise
        else:
            # Modo simulado
            try:
                min_adc = int(float(self.calibration_params.get('min_adc', 0)))
                max_adc = int(float(self.calibration_params.get('max_adc', 32767)))
                logging.debug(f"min_adc: {min_adc}, max_adc: {max_adc}")
            except (TypeError, ValueError) as e:
                logging.error(f"Error en 'min_adc' o 'max_adc' en LevelSensor: {e}")
                min_adc = 0
                max_adc = 32767
            value = random.randint(min_adc, max_adc)
            logging.debug(f"Valor simulado del ADC de nivel en canal {self.channel}: {value}")
            return value

    def calibrar(self, raw_value):
        """
        Convierte el valor bruto del ADC en porcentaje de nivel de agua.
        """
        try:
            min_adc = float(self.calibration_params.get('min_adc', 0))
            max_adc = float(self.calibration_params.get('max_adc', 32767))
            min_level = float(self.calibration_params.get('min_level', 0.0))
            max_level = float(self.calibration_params.get('max_level', 100.0))
            logging.debug(f"Calibración de Nivel: min_adc={min_adc}, max_adc={max_adc}, min_level={min_level}, max_level={max_level}")
        except (TypeError, ValueError) as e:
            logging.error(f"Error en parámetros de calibración en LevelSensor: {e}")
            min_adc, max_adc = 0, 32767
            min_level, max_level = 0.0, 100.0

        if max_adc != min_adc:
            level = (raw_value - min_adc) * (max_level - min_level) / (max_adc - min_adc) + min_level
        else:
            logging.error("max_adc y min_adc son iguales, división por cero en calibración.")
            level = min_level
        level = max(min(level, max_level), min_level)
        logging.debug(f"Valor de nivel calibrado: {level:.2f}%")
        return level

    def detectar_fallo(self):
        """
        Detecta si el sensor de nivel está fallando.
        """
        if self.last_reading is None:
            logging.warning("No se ha podido obtener lectura del sensor de nivel de agua.")
            return True
        return False
