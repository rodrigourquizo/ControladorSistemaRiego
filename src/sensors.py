import random

class HumiditySensor:
    def __init__(self, min_value=30.0, max_value=80.0):
        """
        Inicializa el sensor de humedad con valores mínimos y máximos simulados.
        :param min_value: valor mínimo de humedad (por defecto 30%)
        :param max_value: valor máximo de humedad (por defecto 80%)
        """
        self.min_value = min_value
        self.max_value = max_value
        print("Sensor de Humedad inicializado")

    def leer(self):
        """
        Simula una lectura de humedad en porcentaje.
        :return: valor de humedad entre min_value y max_value
        """
        humedad = random.uniform(self.min_value, self.max_value)
        print(f"Lectura de humedad: {humedad:.2f}%")
        return humedad


class PhSensor:
    def __init__(self, min_value=5.5, max_value=7.5):
        """
        Inicializa el sensor de pH con un rango predefinido.
        :param min_value: valor mínimo de pH (por defecto 5.5)
        :param max_value: valor máximo de pH (por defecto 7.5)
        """
        self.min_value = min_value
        self.max_value = max_value
        print("Sensor de pH inicializado")

    def leer(self):
        """
        Simula una lectura de pH en una escala de 0 a 14.
        :return: valor de pH entre min_value y max_value
        """
        ph = random.uniform(self.min_value, self.max_value)
        print(f"Lectura de pH: {ph:.2f}")
        return ph


class CESensor:
    def __init__(self, min_value=1.0, max_value=3.0):
        """
        Inicializa el sensor de Conductividad Eléctrica (CE) con un rango en mS/cm.
        :param min_value: valor mínimo de CE (por defecto 1.0 mS/cm)
        :param max_value: valor máximo de CE (por defecto 3.0 mS/cm)
        """
        self.min_value = min_value
        self.max_value = max_value
        print("Sensor de Conductividad Eléctrica (CE) inicializado")

    def leer(self):
        """
        Simula una lectura de CE (Conductividad Eléctrica) en miliSiemens por centímetro.
        :return: valor de CE entre min_value y max_value
        """
        ce = random.uniform(self.min_value, self.max_value)
        print(f"Lectura de CE: {ce:.2f} mS/cm")
        return ce


class LevelSensor:
    def __init__(self, min_value=10.0, max_value=100.0):
        """
        Inicializa el sensor de nivel de agua con un rango de valores en porcentaje.
        :param min_value: nivel mínimo de agua en porcentaje (por defecto 10%)
        :param max_value: nivel máximo de agua en porcentaje (por defecto 100%)
        """
        self.min_value = min_value
        self.max_value = max_value
        print("Sensor de Nivel de Agua inicializado")

    def leer(self):
        """
        Simula una lectura del nivel de agua en porcentaje.
        :return: valor del nivel de agua entre min_value y max_value
        """
        nivel = random.uniform(self.min_value, self.max_value)
        print(f"Lectura de nivel de agua: {nivel:.2f}%")
        return nivel

