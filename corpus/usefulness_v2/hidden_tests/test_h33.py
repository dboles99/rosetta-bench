import enum
import unittest
from solution import kind_of


class Level(enum.IntEnum):
    LOW = 1


class TestKindOf(unittest.TestCase):
    def test_true(self):
        self.assertEqual(kind_of(True), "bool")
        self.assertEqual(kind_of(False), "bool")

    def test_one(self):
        self.assertEqual(kind_of(1), "int")

    def test_one_point_zero(self):
        self.assertEqual(kind_of(1.0), "float")

    def test_complex(self):
        self.assertEqual(kind_of(1j), "complex")

    def test_int_subclass(self):
        self.assertEqual(kind_of(Level.LOW), "int")

    def test_errors(self):
        for bad in ("1", None, [1]):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(TypeError, "^not a number: "):
                    kind_of(bad)
