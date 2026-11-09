import unittest
from fractions import Fraction

from solution import evaluate


class EvaluateTests(unittest.TestCase):
    def check(self, expr, expected):
        result = evaluate(expr)
        self.assertEqual(result, expected, expr)
        self.assertIs(type(result), type(expected), expr)

    def test_precedence(self):
        self.check("1+2*3", 7)
        self.check("(1+2)*3", 9)
        self.check(" 10 - 4 - 3 ", 3)
        self.check("16/4/2", 2)

    def test_power_is_right_associative(self):
        self.check("2^3^2", 512)

    def test_unary_minus_binds_looser_than_power(self):
        self.check("-2^2", -4)
        self.check("(-2)^2", 4)
        self.check("-3^2*2", -18)

    def test_negative_exponent_and_unary_after_operator(self):
        self.check("2^-1", Fraction(1, 2))
        self.check("2*-3", -6)
        self.check("3 - -2", 5)
        self.check("--3", 3)

    def test_exact_division(self):
        self.check("7/2", Fraction(7, 2))
        self.check("6/3", 2)
        self.check("1/3+2/3", 1)

    def test_zero_power_zero(self):
        self.check("0^0", 1)

    def test_division_by_zero(self):
        for expr in ("1/0", "1/(2-2)", "0^-1"):
            with self.assertRaises(ZeroDivisionError, msg=expr):
                evaluate(expr)

    def test_syntax_errors(self):
        for expr in ("", "   ", "+1", "2(3)", "2 3", "(1+2", "1+", "1.5", "2^(1/2)", "3 % 2", ")"):
            with self.assertRaises(ValueError, msg=expr):
                evaluate(expr)


if __name__ == "__main__":
    unittest.main()
