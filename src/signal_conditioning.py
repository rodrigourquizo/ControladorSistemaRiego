# signal_conditioning.py

import logging
import numpy as np
from scipy import signal

# Configuración del logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


class SignalConditioning:
    """
    Clase para el acondicionamiento de señales de entrada y salida.
    Proporciona métodos para filtrar ruido, eliminar interferencias y ajustar niveles
    antes de la conversión ADC/DAC o interacción con sensores y actuadores.
    """

    def __init__(self, fs=1.0):
        """
        Inicializa el módulo de acondicionamiento de señal con la frecuencia de muestreo (fs).
        También configura los filtros Butterworth (pasa bajo y pasa alto).

        :param fs: Frecuencia de muestreo en Hz (por defecto 1 Hz para señales lentas).
        """
        self.fs = fs  # Frecuencia de muestreo
        self.nyq = 0.5 * fs  # Frecuencia de Nyquist

        # Almacenar históricos de valores para cada tipo de señal
        self.historicos = {
            'humedad': [],
            'ph': [],
            'ce': [],
            'nivel': []
        }

        logging.info("Módulo de Acondicionamiento de Señal inicializado.")

    def acondicionar_humedad(self, valor):
        """
        Acondiciona la señal de humedad.
        """
        return self._filtrar_valor(valor, 'humedad')

    def acondicionar_ph(self, valor):
        """
        Acondiciona la señal de pH.
        """
        return self._filtrar_valor(valor, 'ph')

    def acondicionar_ce(self, valor):
        """
        Acondiciona la señal de conductividad eléctrica.
        """
        return self._filtrar_valor(valor, 'ce')

    def acondicionar_nivel(self, valor):
        """
        Acondiciona la señal de nivel de agua.
        """
        return self._filtrar_valor(valor, 'nivel')

    def _filtrar_valor(self, valor, tipo):
        """
        Aplica un filtro promedio móvil sencillo al valor para reducir el ruido.

        :param valor: Valor actual del sensor.
        :param tipo: Tipo de sensor ('humedad', 'ph', 'ce', 'nivel').
        :return: Valor filtrado.
        """
        # Obtener el historial correspondiente
        historial = self.historicos.get(tipo, [])
        # Añadir el valor actual al historial
        historial.append(valor)
        # Mantener solo los últimos 5 valores
        if len(historial) > 5:
            historial.pop(0)
        # Actualizar el historial
        self.historicos[tipo] = historial
        # Calcular el promedio de los valores en el historial
        valor_filtrado = np.mean(historial)
        logging.debug(f"Valor filtrado para {tipo}: {valor_filtrado}")
        return valor_filtrado
