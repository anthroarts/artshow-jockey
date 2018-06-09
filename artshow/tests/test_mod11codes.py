from django.test import TestCase
from .. import mod11codes


class Mod11Test (TestCase):
    def test_generation(self):
        self.assertEqual(mod11codes.make_check("196"), "1")
        self.assertEqual(mod11codes.make_check("197"), "X")
        self.assertEqual(mod11codes.make_check("197", check10="@"), "@")
        self.assertEqual(mod11codes.make_check("197", offset=4), "3")

    def test_check_passes(self):
        self.assertIsNone(mod11codes.check("1961"))
        self.assertIsNone(mod11codes.check("197X"))
        self.assertIsNone(mod11codes.check("197@", check10="@"))
        self.assertIsNone(mod11codes.check("1973", offset=4))

    def test_check_failures(self):
        self.assertRaises(mod11codes.CheckDigitError, mod11codes.check, "196X")
        self.assertRaises(mod11codes.CheckDigitError, mod11codes.check, "1970")
        self.assertRaises(mod11codes.CheckDigitError, mod11codes.check, "197X", check10="@")
        self.assertRaises(mod11codes.CheckDigitError, mod11codes.check, "197X", offset=4)
