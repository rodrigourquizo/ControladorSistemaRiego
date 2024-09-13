from sensors import HumiditySensor, PhSensor, CESensor, LevelSensor
from actuators import PumpControl, ValveControl
from signal_conditioning import SignalConditioning
from decision_engine import DecisionEngine
from cloud_sync import CloudSync
from model_training import ModelTraining
from gui import NodeRedInterface
import time

class ControladorSistemaRiego:
    def __init__(self):
        # Inicialización de sensores
        self.humidity_sensor = HumiditySensor()
        self.ph_sensor = PhSensor()
        self.ce_sensor = CESensor()
        self.level_sensor = LevelSensor()

        # Inicialización de actuadores
        self.pump_control = PumpControl()
        self.valve_control = ValveControl()

        # Acondicionamiento de señal
        self.signal_conditioning = SignalConditioning()

        # Motor de toma de decisiones con Machine Learning
        self.decision_engine = DecisionEngine()

        # Sincronización con la nube
        self.cloud_sync = CloudSync()

        # Entrenamiento del modelo en la nube y localmente
        self.model_training = ModelTraining()

        # Interfaz gráfica en Node-RED
        self.gui = NodeRedInterface()

        # Parámetros del sistema
        self.data_collection_frequency = 60  # Frecuencia de recolección de datos (en segundos)
        self.offline_mode = True  # Inicialmente en modo offline
        self.sensor_data = []  # Lista para almacenar los datos de los sensores

        print("Controlador del Sistema de Riego inicializado.")

    def iniciar(self):
        print("Iniciando el sistema de riego...")
        while True:
            # 1. Adquisición de datos de sensores
            sensor_values = self._leer_sensores()

            # 2. Verificar conexión a internet y sincronizar si es posible
            if self._verificar_conexion_internet():
                self.offline_mode = False
                self._sincronizar_con_nube(sensor_values)
            else:
                self.offline_mode = True

            # 3. Procesar los datos con la lógica de toma de decisiones
            self._procesar_datos(sensor_values)

            # 4. Enviar los datos a la interfaz gráfica Node-RED
            self.gui.enviar_datos_a_nodered(sensor_values)

            # Intervalo de espera para la próxima recolección de datos
            time.sleep(self.data_collection_frequency)

    def _leer_sensores(self):
        """Adquiere y acondiciona los datos de todos los sensores."""
        print("Leyendo datos de sensores...")

        # Lectura de los sensores
        humidity = self.humidity_sensor.leer()
        ph = self.ph_sensor.leer()
        ce = self.ce_sensor.leer()
        water_level = self.level_sensor.leer()

        # Acondicionamiento de señales
        humidity = self.signal_conditioning.acondicionar_entrada(humidity)
        ph = self.signal_conditioning.acondicionar_entrada(ph)
        ce = self.signal_conditioning.acondicionar_entrada(ce)
        water_level = self.signal_conditioning.acondicionar_entrada(water_level)

        # Agrupación de datos en un diccionario
        sensor_values = {
            'humidity': humidity,
            'ph': ph,
            'ce': ce,
            'water_level': water_level
        }

        print(f"Datos adquiridos: {sensor_values}")
        self.sensor_data.append(sensor_values)  # Almacenar los datos para análisis

        return sensor_values

    def _procesar_datos(self, sensor_values):
        """Procesa los datos adquiridos y toma decisiones basadas en Machine Learning."""
        print("Procesando datos y tomando decisiones...")

        # Evaluar los datos utilizando el motor de decisiones (Random Forest)
        decision = self.decision_engine.tomar_decision(sensor_values)

        # Tomar decisiones sobre los actuadores según la evaluación
        if decision['activar_riego']:
            print("Activando riego...")
            self._accionar_actuadores(decision)
        else:
            print("Condiciones óptimas, no es necesario el riego.")

    def _accionar_actuadores(self, decision):
        """Controla los actuadores (bomba y válvulas) según la decisión tomada."""
        if decision['activar_bomba']:
            self.pump_control.activar()
        else:
            self.pump_control.desactivar()

        if decision['abrir_valvula']:
            self.valve_control.abrir()
        else:
            self.valve_control.cerrar()

        if decision['inyeccion_fertilizante']:
            print("Inyectando fertilizante según la lectura de CE...")

    def _sincronizar_con_nube(self, sensor_values):
        """Sincroniza los datos con la nube y actualiza el modelo desde la nube."""
        print("Sincronizando datos con la nube...")
        self.cloud_sync.enviar_datos(sensor_values)
        self.model_training.actualizar_modelo()

    def _verificar_conexion_internet(self):
        """Simula la verificación de la conexión a internet."""
        # Aquí puedes implementar una verificación real de conexión a internet
        # Simulación: retorna True cada 5 ciclos para simular conexión intermitente
        return len(self.sensor_data) % 5 == 0

# Ejemplo de ejecución del sistema
if __name__ == "__main__":
    controlador = ControladorSistemaRiego()
    controlador.iniciar()
