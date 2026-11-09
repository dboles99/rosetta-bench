import unittest
from solution import parse_port


class TestParsePort(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(parse_port("80"), 80)
        self.assertEqual(parse_port("65535"), 65535)
        self.assertEqual(parse_port("1"), 1)

    def test_strip(self):
        self.assertEqual(parse_port(" 443\n"), 443)

    def test_zero_out_of_range(self):
        with self.assertRaisesRegex(ValueError, "^port out of range: "):
            parse_port("0")

    def test_too_big(self):
        with self.assertRaisesRegex(ValueError, "^port out of range: "):
            parse_port("65536")

    def test_invalid_forms(self):
        for bad in ("+80", "-1", "8_0", "8 0", "\uff18\uff10", "080", "00", "", "   ", "eighty", "8.0"):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(ValueError, "^invalid port: "):
                    parse_port(bad)

    def test_returns_int(self):
        self.assertIs(type(parse_port("8080")), int)
