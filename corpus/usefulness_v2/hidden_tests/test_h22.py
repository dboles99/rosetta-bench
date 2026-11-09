import unittest
from decimal import Decimal

from solution import Ledger, InsufficientFunds


class TestLedger(unittest.TestCase):
    def test_exact_decimal_arithmetic(self):
        ledger = Ledger()
        ledger.deposit("0.10")
        ledger.deposit("0.20")
        self.assertEqual(ledger.balance(), "0.30")

    def test_withdraw_to_zero_has_no_fee(self):
        ledger = Ledger()
        ledger.deposit("10")
        ledger.withdraw("10")
        self.assertEqual(ledger.balance(), "0.00")
        self.assertEqual(ledger.history(), [("deposit", "10.00"), ("withdraw", "10.00")])

    def test_negative_balance_charges_fee(self):
        ledger = Ledger("50.00")
        ledger.deposit("10")
        ledger.withdraw("30")
        self.assertEqual(ledger.balance(), "-21.50")
        self.assertEqual(ledger.history()[-2:], [("withdraw", "30.00"), ("fee", "1.50")])

    def test_limit_boundary_and_fee_may_exceed_limit(self):
        ledger = Ledger("50.00")
        ledger.deposit("10")
        ledger.withdraw("30")
        with self.assertRaises(InsufficientFunds):
            ledger.withdraw("28.51")
        self.assertEqual(ledger.balance(), "-21.50")
        ledger.withdraw("28.50")
        self.assertEqual(ledger.balance(), "-51.50")

    def test_fee_on_every_withdrawal_that_ends_negative(self):
        ledger = Ledger("100")
        ledger.withdraw("10")
        self.assertEqual(ledger.balance(), "-11.50")
        ledger.withdraw("1")
        self.assertEqual(ledger.balance(), "-14.00")

    def test_default_limit_is_zero(self):
        ledger = Ledger()
        ledger.deposit("5")
        with self.assertRaises(InsufficientFunds):
            ledger.withdraw("5.01")
        self.assertEqual(ledger.balance(), "5.00")
        self.assertEqual(len(ledger.history()), 1)

    def test_insufficient_funds_is_not_a_value_error(self):
        self.assertTrue(issubclass(InsufficientFunds, Exception))
        self.assertFalse(issubclass(InsufficientFunds, ValueError))

    def test_invalid_amount_formats(self):
        ledger = Ledger()
        for bad in ("1.234", "-5", "0", "0.00", "abc", "1e2", " 5", "5 ", "", "1.", "+5", "５", ".5"):
            with self.assertRaises(ValueError, msg=repr(bad)):
                ledger.deposit(bad)
            with self.assertRaises(ValueError, msg=repr(bad)):
                ledger.withdraw(bad)
        self.assertEqual(ledger.history(), [])

    def test_non_string_amounts(self):
        ledger = Ledger()
        for bad in (5, Decimal("5"), 5.0):
            with self.assertRaises(TypeError):
                ledger.deposit(bad)
        with self.assertRaises(TypeError):
            ledger.withdraw(5)
        with self.assertRaises(TypeError):
            Ledger(10)

    def test_overdraft_limit_validation(self):
        self.assertEqual(Ledger("0").balance(), "0.00")
        with self.assertRaises(ValueError):
            Ledger("-1")

    def test_history_is_a_copy_and_formats_amounts(self):
        ledger = Ledger()
        ledger.deposit("10.5")
        history = ledger.history()
        history.append(("deposit", "999.00"))
        self.assertEqual(ledger.history(), [("deposit", "10.50")])


if __name__ == "__main__":
    unittest.main()
