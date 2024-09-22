import logging

class Amplifier:
    """
    Clase para manejar amplificadores de señal.
    """
    def __init__(self, gain=1):
        self.gain = gain
        logging.info(f"Amplificador inicializado con ganancia {self.gain}.")

    def set_gain(self, gain):
        self.gain = gain
        logging.info(f"Ganancia ajustada a {self.gain}.")

    def amplify(self, signal):
        amplified_signal = signal * self.gain
        return amplified_signal

# Agrega aquí métodos de interacciòn con el hardware .
