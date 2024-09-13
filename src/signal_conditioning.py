from scipy import signal

class SignalConditioning:
    def __init__(self):
        """
        Inicializa el módulo de acondicionamiento de señal, encargado de procesar las señales 
        antes de ser enviadas al ADC (entrada) o desde el DAC (salida).
        """
        print("Acondicionamiento de Señal inicializado")

    def acondicionar_entrada(self, valor):
        """
        Simula el acondicionamiento de la señal de entrada proveniente de un sensor antes 
        de enviarla al ADC. Se usa un filtro para reducir el ruido en la señal.
        :param valor: Valor de la señal proveniente del sensor.
        :return: Valor filtrado y acondicionado.
        """
        # Aplicamos un filtro para eliminar ruido de la señal
        valor_filtrado = self.filtrar_ruido(valor)
        print(f"Valor de entrada acondicionado: {valor_filtrado:.2f}")
        return valor_filtrado

    def acondicionar_salida(self, valor):
        """
        Acondiciona la señal de salida antes de enviarla a los actuadores (ej. DAC).
        Este método puede ser útil para ajustar las señales que activan los actuadores.
        :param valor: Valor de salida que será enviado al actuador.
        :return: Valor procesado (actualmente no hay procesamiento adicional).
        """
        # Por ahora no se realiza acondicionamiento de salida, pero este método está preparado
        # para futuras expansiones donde se requiera modificar la señal antes de enviarla al DAC.
        print(f"Valor de salida sin acondicionar: {valor:.2f}")
        return valor

    def filtrar_ruido(self, valor):
        """
        Aplica un filtro paso bajo para reducir el ruido en la señal.
        :param valor: Valor de la señal a filtrar.
        :return: Valor filtrado, suavizado para reducir el ruido.
        """
        # Se usa un filtro de Butterworth de orden 3, con una frecuencia de corte baja (0.05)
        b, a = signal.butter(3, 0.05)  # Filtro paso bajo de orden 3
        # Filtramos la señal utilizando el filtro diseñado
        valor_filtrado = signal.filtfilt(b, a, [valor])[0]
        print(f"Valor filtrado (ruido reducido): {valor_filtrado:.2f}")
        return valor_filtrado
