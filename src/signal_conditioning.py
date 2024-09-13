from scipy import signal

class SignalConditioning:
    def __init__(self):
        print("Acondicionamiento de Señal inicializado")

    def acondicionar_entrada(self, valor):
        """Simulación del acondicionamiento de la señal antes de pasar al ADC."""
        # Ejemplo simple de filtro paso bajo usando SciPy
        # Creamos una señal suave para simular el acondicionamiento
        valor_filtrado = self.filtrar_ruido(valor)
        return valor_filtrado

    def acondicionar_salida(self, valor):
        """Acondiciona la señal de salida para los actuadores (ej. DAC)."""
        # Aquí podrías acondicionar señales de salida si fuese necesario
        # Actualmente no tenemos lógica para esto, pero se puede extender
        return valor

    def filtrar_ruido(self, valor):
        """Filtro simple de ruido usando una ventana de suavizado (SciPy)"""
        # Aplicamos una media móvil simple para reducir el ruido
        # En una aplicación real, podrías usar un filtro más sofisticado
        b, a = signal.butter(3, 0.05)  # Filtro paso bajo
        valor_filtrado = signal.filtfilt(b, a, [valor])[0]
        return valor_filtrado
