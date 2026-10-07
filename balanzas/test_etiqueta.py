import unittest
from balanzas.etiqueta import digito_verificador, ean13_valido, parsear_etiqueta


def armar(cuerpo):
    return cuerpo + str(digito_verificador(cuerpo))


class Etiqueta(unittest.TestCase):
    def test_ean_conocido(self):
        self.assertEqual(digito_verificador("400638133393"), 1)
        self.assertTrue(ean13_valido("4006381333931"))
        self.assertFalse(ean13_valido("4006381333932"))

    def test_decodifica(self):
        cod = armar("20" + "0012" + "001850")       # PLU 12, importe 1850
        self.assertEqual(parsear_etiqueta("20PPPPIIIIII", cod), (12, 1850))

    def test_prefijo_distinto(self):
        cod = armar("21" + "0012" + "001850")
        self.assertIsNone(parsear_etiqueta("20PPPPIIIIII", cod))

    def test_checksum_mal(self):
        cod = armar("20" + "0012" + "001850")
        malo = cod[:-1] + str((int(cod[-1]) + 1) % 10)
        self.assertIsNone(parsear_etiqueta("20PPPPIIIIII", malo))

    def test_otros_formatos(self):
        cod = armar("2" + "000012" + "01850" )       # 2 + PLU6 + importe5
        self.assertEqual(parsear_etiqueta("2PPPPPPIIIII", cod), (12, 1850))
        self.assertIsNone(parsear_etiqueta("20PPPPIIIIII", "123"))
        self.assertIsNone(parsear_etiqueta("20PPPPIIIIII", armar("20" + "0000" + "001850")))  # PLU 0


if __name__ == "__main__":
    unittest.main()
