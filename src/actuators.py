class PumpControl:
    def __init__(self):
        """
        Inicializa el control de la bomba hidráulica. La bomba comienza en estado 'apagada'.
        """
        self.estado = False  # La bomba está inicialmente apagada
        print("Control de la Bomba Hidráulica inicializado.")

    def activar(self):
        """
        Activa la bomba hidráulica si no está ya activada.
        """
        if not self.estado:
            self.estado = True
            print("Bomba activada.")
        else:
            print("La bomba ya está activada.")

    def desactivar(self):
        """
        Desactiva la bomba hidráulica si está activada.
        """
        if self.estado:
            self.estado = False
            print("Bomba desactivada.")
        else:
            print("La bomba ya está desactivada.")

    def estado_actual(self):
        """
        Devuelve el estado actual de la bomba (True para activada, False para desactivada).
        :return: Estado de la bomba.
        """
        return self.estado


class ValveControl:
    def __init__(self):
        """
        Inicializa el control de las electroválvulas. Las válvulas comienzan en estado 'cerrado'.
        """
        self.estado = False  # Las válvulas están inicialmente cerradas
        print("Control de Electroválvulas inicializado.")

    def abrir(self):
        """
        Abre las válvulas si no están ya abiertas.
        """
        if not self.estado:
            self.estado = True
            print("Válvulas abiertas.")
        else:
            print("Las válvulas ya están abiertas.")

    def cerrar(self):
        """
        Cierra las válvulas si están abiertas.
        """
        if self.estado:
            self.estado = False
            print("Válvulas cerradas.")
        else:
            print("Las válvulas ya están cerradas.")

    def estado_actual(self):
        """
        Devuelve el estado actual de las válvulas (True para abiertas, False para cerradas).
        :return: Estado de las válvulas.
        """
        return self.estado

