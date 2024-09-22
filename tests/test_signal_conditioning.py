import unittest
from signal_conditioning import SignalConditioning

class TestSignalConditioning(unittest.TestCase):

    def setUp(self):
        self.signal_conditioning = SignalConditioning()

    def test_acondicionar_humedad(self):
        valor = self.signal_conditioning.acondicionar_humedad(50)
        self.assertIsNotNone(valor)

if __name__ == '__main__':
    unittest.main()
