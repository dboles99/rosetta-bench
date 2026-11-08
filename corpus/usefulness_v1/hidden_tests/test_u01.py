import unittest
from solution import canonical_packet


class AcceptanceTests(unittest.TestCase):
    def test_order_and_format(self):
        self.assertEqual(canonical_packet("1.0", {"B": 3, "A": "x"}), "SCHEMA_VER=1.0\nA=x\nB=3\n")
    def test_floats_two_decimals(self):
        self.assertEqual(canonical_packet("1.0", {"T": 0.5}), "SCHEMA_VER=1.0\nT=0.50\n")
    def test_empty_fields(self):
        self.assertEqual(canonical_packet("2.1", {}), "SCHEMA_VER=2.1\n")
    def test_no_carriage_returns(self):
        self.assertNotIn("\r", canonical_packet("1.0", {"A": 1, "B": 2.0}))
