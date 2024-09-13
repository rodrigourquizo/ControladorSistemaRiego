from controller import ControladorSistemaRiego

if __name__ == "__main__":
    """
    Punto de entrada principal del sistema de riego.
    Aquí se inicializa el controlador principal del sistema de riego y se llama 
    al método que gestiona el inicio de todas las operaciones.
    """
    try:
        # Inicializamos el controlador del sistema de riego
        controlador = ControladorSistemaRiego()
        
        # Iniciamos el sistema de riego
        controlador.iniciar()

    except KeyboardInterrupt:
        # Manejo de la interrupción del teclado (Ctrl + C)
        print("\nSistema de riego detenido manualmente.")

    except Exception as e:
        # Captura de cualquier otra excepción no prevista para su depuración
        print(f"Error inesperado: {e}")
