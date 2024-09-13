class PumpControl:
    def __init__(self):
        self.estado = False  # Inicialmente la bomba está apagada
        print("Control de la Bomba Hidráulica inicializado")

    def activar(self):
        self.estado = True
        print("Bomba activada")

    def desactivar(self):
        self.estado = False
        print("Bomba desactivada")


class ValveControl:
    def __init__(self):
        self.estado = False  # Inicialmente las válvulas están cerradas
        print("Control de Electroválvulas inicializado")

    def abrir(self):
        self.estado = True
        print("Válvulas abiertas")

    def cerrar(self):
        self.estado = False
        print("Válvulas cerradas")
