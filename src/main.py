# main.py

import logging
import sys
from controller import ControladorSistemaRiego

# Configuración del logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def main():
    """
    Punto de entrada principal del sistema de riego.
    Inicializa el controlador principal del sistema de riego y gestiona el ciclo principal de operaciones.
    """
    try:
        logging.info("Iniciando el sistema de riego automático.")

        # Inicializamos el controlador del sistema de riego
        controlador = ControladorSistemaRiego()

        # Iniciamos el sistema de riego
        controlador.iniciar()

    except KeyboardInterrupt:
        # Manejo de la interrupción del teclado (Ctrl + C)
        logging.info("Sistema de riego detenido manualmente por el usuario.")

    except Exception as e:
        # Captura de cualquier otra excepción no prevista para su depuración
        logging.error(f"Error inesperado en el sistema: {e}", exc_info=True)

    finally:
        # Realizar tareas de limpieza y liberación de recursos si es necesario
        logging.info("Sistema de riego finalizado.")

if __name__ == "__main__":
    main()
