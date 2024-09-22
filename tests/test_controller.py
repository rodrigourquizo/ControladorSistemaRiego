import unittest
from controller import ControladorSistemaRiego
from unittest.mock import patch

class TestController(unittest.TestCase):

    @patch('controller.ControladorSistemaRiego._leer_sensores')
    @patch('controller.ControladorSistemaRiego._accionar_actuadores')
    def test_control_flow(self, mock_leer, mock_accionar):
        controlador = ControladorSistemaRiego()
        mock_leer.return_value = {'humidity': 45, 'ph': 6.5, 'ce': 1.2, 'water_level': 70}
        controlador.iniciar()
        mock_leer.assert_called_once()
        mock_accionar.assert_called_once()

if __name__ == '__main__':
    unittest.main()
