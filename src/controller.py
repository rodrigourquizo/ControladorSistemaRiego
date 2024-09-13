from sensors import HumiditySensor, PhSensor, CESensor, LevelSensor  # Importamos los módulos de sensores específicos
from actuators import PumpControl, ValveControl  # Importamos los módulos para controlar la bomba y válvulas
from signal_conditioning import SignalConditioning  # Módulo para acondicionar señales de entrada y salida
from decision_engine import DecisionEngine  # Motor de toma de decisiones basado en Machine Learning
from cloud_sync import CloudSync  # Sincronización de datos con la nube (Google Cloud Platform)
from model_training import ModelTraining  # Entrenamiento y actualización del modelo de Machine Learning
from gui import NodeRedInterface  # Interfaz gráfica con Node-RED para visualizar y controlar el sistema
import time  # Módulo para manejar el tiempo de espera entre recolecciones de datos

class ControladorSistemaRiego:
    def __init__(self):
        # Inicialización de sensores
        self.humidity_sensor = HumiditySensor()  # Sensor de humedad del suelo
        self.ph_sensor = PhSensor()  # Sensor de pH del agua o del suelo
        self.ce_sensor = CESensor()  # Sensor de conductividad eléctrica (CE) para medir nutrientes en el agua
        self.level_sensor = LevelSensor()  # Sensor de nivel de agua en el tanque de almacenamiento

        # Inicialización de actuadores
        self.pump_control = PumpControl()  # Control de la bomba hidráulica para el riego
        self.valve_control = ValveControl()  # Control de las electroválvulas para dirigir el flujo de agua

        # Acondicionamiento de señal
        self.signal_conditioning = SignalConditioning()  # Módulo para acondicionar las señales de los sensores antes de pasarlas al ADC

        # Motor de toma de decisiones con Machine Learning
        self.decision_engine = DecisionEngine()  # Motor de decisiones basado en el modelo Random Forest

        # Sincronización con la nube
        self.cloud_sync = CloudSync()  # Sincronización de datos con Google Cloud Platform

        # Entrenamiento del modelo en la nube y localmente
        self.model_training = ModelTraining()  # Módulo encargado del entrenamiento y actualización del modelo de predicción

        # Interfaz gráfica en Node-RED
        self.gui = NodeRedInterface()  # Interfaz para la visualización y control en tiempo real

        # Parámetros del sistema
        self.data_collection_frequency = 60  # Frecuencia de recolección de datos en segundos (ajustable según necesidades del sistema)
        self.offline_mode = True  # Inicialmente el sistema está en modo offline (sin conexión a internet)
        self.sensor_data = []  # Lista para almacenar los datos de los sensores recolectados para análisis y sincronización

        print("Controlador del Sistema de Riego inicializado.")  # Mensaje de confirmación de inicialización

    def iniciar(self):
        print("Iniciando el sistema de riego...")  # Mensaje de inicio
        while True:
            # 1. Adquisición de datos de sensores
            sensor_values = self._leer_sensores()  # Se obtienen los datos de los sensores

            # 2. Verificar conexión a internet y sincronizar si es posible
            if self._verificar_conexion_internet():  # Verificamos si hay conexión a internet
                self.offline_mode = False  # Si hay conexión, cambiamos a modo online
                self._sincronizar_con_nube(sensor_values)  # Sincronizamos los datos con la nube
            else:
                self.offline_mode = True  # Si no hay conexión, mantenemos el modo offline

            # 3. Procesar los datos con la lógica de toma de decisiones
            self._procesar_datos(sensor_values)  # Procesamos los datos para decidir si es necesario regar o no

            # 4. Enviar los datos a la interfaz gráfica Node-RED
            self.gui.enviar_datos_a_nodered(sensor_values)  # Enviamos los datos para visualización en la interfaz gráfica

            # Intervalo de espera para la próxima recolección de datos
            time.sleep(self.data_collection_frequency)  # Esperamos el intervalo definido antes de la próxima lectura de sensores

    def _leer_sensores(self):
        """Adquiere y acondiciona los datos de todos los sensores."""
        print("Leyendo datos de sensores...")

        # Lectura de los sensores
        humidity = self.humidity_sensor.leer()  # Lectura del sensor de humedad
        ph = self.ph_sensor.leer()  # Lectura del sensor de pH
        ce = self.ce_sensor.leer()  # Lectura del sensor de conductividad eléctrica (CE)
        water_level = self.level_sensor.leer()  # Lectura del nivel de agua en el tanque

        # Acondicionamiento de señales antes de pasarlas al ADC
        humidity = self.signal_conditioning.acondicionar_entrada(humidity)
        ph = self.signal_conditioning.acondicionar_entrada(ph)
        ce = self.signal_conditioning.acondicionar_entrada(ce)
        water_level = self.signal_conditioning.acondicionar_entrada(water_level)

        # Agrupación de datos en un diccionario para manejarlos más fácilmente
        sensor_values = {
            'humidity': humidity,
            'ph': ph,
            'ce': ce,
            'water_level': water_level
        }

        print(f"Datos adquiridos: {sensor_values}")  # Mostramos los valores adquiridos
        self.sensor_data.append(sensor_values)  # Almacenamos los datos para análisis y sincronización

        return sensor_values  # Retornamos los valores de los sensores

    def _procesar_datos(self, sensor_values):
        """Procesa los datos adquiridos y toma decisiones basadas en Machine Learning."""
        print("Procesando datos y tomando decisiones...")

        # Evaluar los datos utilizando el motor de decisiones (Random Forest)
        decision = self.decision_engine.tomar_decision(sensor_values)  # Usamos el modelo para tomar una decisión basada en los datos

        # Tomar decisiones sobre los actuadores según la evaluación
        if decision['activar_riego']:
            print("Activando riego...")  # Si es necesario, activamos el riego
            self._accionar_actuadores(decision)
        else:
            print("Condiciones óptimas, no es necesario el riego.")  # Si no es necesario, no hacemos nada

    def _accionar_actuadores(self, decision):
        """Controla los actuadores (bomba y válvulas) según la decisión tomada."""
        if decision['activar_bomba']:
            self.pump_control.activar()  # Activamos la bomba si la decisión lo requiere
        else:
            self.pump_control.desactivar()  # Si no, desactivamos la bomba

        if decision['abrir_valvula']:
            self.valve_control.abrir()  # Abrimos las válvulas si es necesario
        else:
            self.valve_control.cerrar()  # Si no, cerramos las válvulas

        if decision['inyeccion_fertilizante']:
            print("Inyectando fertilizante según la lectura de CE...")  # Si es necesario, inyectamos fertilizante

    def _sincronizar_con_nube(self, sensor_values):
        """Sincroniza los datos con la nube y actualiza el modelo desde la nube."""
        print("Sincronizando datos con la nube...")
        self.cloud_sync.enviar_datos(sensor_values)  # Enviamos los datos a la nube
        self.model_training.actualizar_modelo()  # Actualizamos el modelo de Machine Learning

    def _verificar_conexion_internet(self):
        """Simula la verificación de la conexión a internet."""
        # Aquí puedes implementar una verificación real de conexión a internet
        # Simulación: retorna True cada 5 ciclos para simular conexión intermitente
        return len(self.sensor_data) % 5 == 0  # Retorna True cada 5 ciclos para simular intermitencia en la conexión

# Ejemplo de ejecución del sistema
if __name__ == "__main__":
    controlador = ControladorSistemaRiego()  # Creamos una instancia del controlador del sistema de riego
    controlador.iniciar()  # Iniciamos el sistema de riego

