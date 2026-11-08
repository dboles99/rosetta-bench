import unittest
from solution import parse_packet


class AcceptanceTests(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(parse_packet("SCHEMA_VER=1.0\nA=1\n"), ("1.0", {"A": "1"}))
    def test_value_with_equals(self):
        self.assertEqual(parse_packet("SCHEMA_VER=1.0\nURL=a=b\n")[1], {"URL": "a=b"})
    def test_blank_and_junk_lines(self):
        self.assertEqual(parse_packet("\n  SCHEMA_VER=1.0  \nnoequals\n\nB=2\n"), ("1.0", {"B": "2"}))
    def test_missing_schema(self):
        with self.assertRaises(ValueError):
            parse_packet("A=1\n")
