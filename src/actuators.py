# actuators.py

import time
import logging
import sys

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


class ActuatorBase:
    """
    Clase base para los actuadores. Proporciona métodos para inicialización,
    activación, desactivación y manejo de estado.
    """
    def __init__(self, gpio_pin, nombre_actuador="Actuador", active_low=False):
        """
        Inicializa el actuador en el pin GPIO especificado.

        :param gpio_pin: Número del pin GPIO al que está conectado el actuador.
        :param nombre_actuador: Nombre descriptivo del actuador.
        :param active_low: Indica si el actuador se activa con una señal baja (GPIO.LOW).
        """
        self.gpio_pin = gpio_pin
        self.nombre_actuador = nombre_actuador
        self.estado = False  # Estado inicial: desactivado
        self.active_low = active_low  # Control de lógica inversa

        self.simulation_mode = sys.platform == "win32" or GPIO is None

        if not self.simulation_mode:
            GPIO.setmode(GPIO.BCM)  # Usar numeración BCM
            GPIO.setup(self.gpio_pin, GPIO.OUT)
            # Establecer estado inicial
            if self.active_low:
                GPIO.output(self.gpio_pin, GPIO.HIGH)  # Estado inicial apagado
            else:
                GPIO.output(self.gpio_pin, GPIO.LOW)  # Estado inicial apagado
            logging.info(f"{self.nombre_actuador} inicializado en pin GPIO {self.gpio_pin}.")
        else:
            logging.info(f"{self.nombre_actuador} inicializado en modo simulado.")

    def activar(self):
        """
        Activa el actuador si no está ya activado.
        """
        if not self.estado:
            self.estado = True
            if not self.simulation_mode:
                if self.active_low:
                    GPIO.output(self.gpio_pin, GPIO.LOW)
                else:
                    GPIO.output(self.gpio_pin, GPIO.HIGH)
            logging.info(f"{self.nombre_actuador} activado.")
        else:
            logging.debug(f"{self.nombre_actuador} ya estaba activado.")

    def desactivar(self):
        """
        Desactiva el actuador si está activado.
        """
        if self.estado:
            self.estado = False
            if not self.simulation_mode:
                if self.active_low:
                    GPIO.output(self.gpio_pin, GPIO.HIGH)
                else:
                    GPIO.output(self.gpio_pin, GPIO.LOW)
            logging.info(f"{self.nombre_actuador} desactivado.")
        else:
            logging.debug(f"{self.nombre_actuador} ya estaba desactivado.")

    def estado_actual(self):
        """
        Devuelve el estado actual del actuador.

        :return: True si está activado, False si está desactivado.
        """
        return self.estado

    def limpiar(self):
        """
        Limpia la configuración del GPIO para este actuador.
        """
        if not self.simulation_mode:
            GPIO.cleanup(self.gpio_pin)
            logging.info(f"GPIO {self.gpio_pin} limpiado para {self.nombre_actuador}.")
        else:
            logging.info(f"Simulación de limpieza del GPIO para {self.nombre_actuador}.")


class PumpControl(ActuatorBase):
    """
    Control de la bomba hidráulica.
    """
    def __init__(self, gpio_pin):
        # Suponiendo que la bomba se activa en alto, active_low=False
        super().__init__(gpio_pin, nombre_actuador="Bomba Hidráulica", active_low=False)


class ValveControl:
    """
    Control de las electroválvulas. Maneja múltiples válvulas.
    """
    def __init__(self, valvulas_config):
        """
        Inicializa las electroválvulas según la configuración proporcionada.

        :param valvulas_config: Diccionario con la configuración de las válvulas.
                                Ejemplo:
                                {
                                    'valvula_riego': gpio_pin_riego,
                                    'valvula_suministro': gpio_pin_suministro,
                                    'valvula_fertilizante': gpio_pin_fertilizante
                                }
        """
        self.valvulas = {}
        for nombre, pin in valvulas_config.items():
            # Suponiendo que las válvulas se activan en bajo (común en módulos de relés)
            self.valvulas[nombre] = ActuatorBase(pin, nombre_actuador=f"Válvula {nombre}", active_low=True)
        logging.info("Control de Electroválvulas inicializado.")

    def abrir_valvula(self, nombre_valvula):
        """
        Abre la válvula especificada si no está ya abierta.

        :param nombre_valvula: Nombre de la válvula a abrir.
        """
        valvula = self.valvulas.get(nombre_valvula)
        if valvula:
            valvula.activar()
        else:
            logging.error(f"Válvula '{nombre_valvula}' no encontrada.")

    def cerrar_valvula(self, nombre_valvula):
        """
        Cierra la válvula especificada si está abierta.

        :param nombre_valvula: Nombre de la válvula a cerrar.
        """
        valvula = self.valvulas.get(nombre_valvula)
        if valvula:
            valvula.desactivar()
        else:
            logging.error(f"Válvula '{nombre_valvula}' no encontrada.")

    def estado_actual(self, nombre_valvula):
        """
        Devuelve el estado actual de la válvula especificada.

        :param nombre_valvula: Nombre de la válvula.
        :return: True si está abierta, False si está cerrada.
        """
        valvula = self.valvulas.get(nombre_valvula)
        if valvula:
            return valvula.estado_actual()
        else:
            logging.error(f"Válvula '{nombre_valvula}' no encontrada.")
            return None

    def limpiar(self):
        """
        Limpia la configuración del GPIO para todas las válvulas.
        """
        for valvula in self.valvulas.values():
            valvula.limpiar()
        logging.info("Configuración de electroválvulas limpiada.")
