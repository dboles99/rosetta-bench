import unittest
from solution import coerce_numeric


class AcceptanceTests(unittest.TestCase):
    SCHEMA = {"properties": {"N": {"type": "integer"}, "P": {"type": "number"}, "S": {"type": "string"}}}
    def test_converts(self):
        self.assertEqual(coerce_numeric({"N": "3", "P": "0.5", "S": "x"}, self.SCHEMA), {"N": 3, "P": 0.5, "S": "x"})
    def test_bad_values_kept(self):
        self.assertEqual(coerce_numeric({"N": "three"}, self.SCHEMA), {"N": "three"})
    def test_unknown_and_non_string(self):
        self.assertEqual(coerce_numeric({"Z": "1", "N": 4}, self.SCHEMA), {"Z": "1", "N": 4})
    def test_input_untouched(self):
        fields = {"N": "3"}
        coerce_numeric(fields, self.SCHEMA)
        self.assertEqual(fields, {"N": "3"})
