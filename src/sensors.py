import random

class HumiditySensor:
    def __init__(self):
        print("Sensor de Humedad inicializado")

    def leer(self):
        # Simulamos una lectura del sensor de humedad en porcentaje
        humedad = random.uniform(30.0, 80.0)  # Simulación de valores entre 30% y 80%
        print(f"Lectura de humedad: {humedad:.2f}%")
        return humedad


class PhSensor:
    def __init__(self):
        print("Sensor de pH inicializado")

    def leer(self):
        # Simulamos una lectura del sensor de pH (escala 0-14)
        ph = random.uniform(5.5, 7.5)  # Simulación de valores de pH entre 5.5 y 7.5
        print(f"Lectura de pH: {ph:.2f}")
        return ph


class CESensor:
    def __init__(self):
        print("Sensor de Conductividad Eléctrica (CE) inicializado")

    def leer(self):
        # Simulamos una lectura de CE en miliSiemens por cm (mS/cm)
        ce = random.uniform(1.0, 3.0)  # Simulación de valores de CE entre 1 y 3 mS/cm
        print(f"Lectura de CE: {ce:.2f} mS/cm")
        return ce


class LevelSensor:
    def __init__(self):
        print("Sensor de Nivel de Agua inicializado")

    def leer(self):
        # Simulamos una lectura de nivel de agua (0 - 100%) en el tanque
        nivel = random.uniform(10.0, 100.0)  # Simulación de valores de nivel entre 10% y 100%
        print(f"Lectura de nivel de agua: {nivel:.2f}%")
        return nivel
