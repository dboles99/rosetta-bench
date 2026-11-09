import random
import time
import unittest
from decimal import Decimal
from solution import FifoBook


class TestFifoBook(unittest.TestCase):
    def test_fifo_partial_lots(self):
        book = FifoBook()
        book.buy(10, "5.00")
        book.buy(10, "6.00")
        self.assertEqual(book.sell(15, "7.00"), Decimal("25.00"))
        self.assertEqual(book.lots(), [(5, "6.00")])
        self.assertEqual(book.holdings(), 5)

    def test_profit_is_decimal_and_can_be_negative(self):
        book = FifoBook()
        book.buy(3, "10")
        result = book.sell(3, "9.5")
        self.assertIsInstance(result, Decimal)
        self.assertEqual(result, Decimal("-1.50"))
        self.assertEqual(str(result), "-1.50")

    def test_each_sell_rounded_half_even_before_summing(self):
        book = FifoBook()
        book.buy(2, "1.0000")
        self.assertEqual(book.sell(1, "1.0050"), Decimal("0.00"))  # 0.005 -> 0.00 (half even)
        self.assertEqual(book.sell(1, "1.0150"), Decimal("0.02"))  # 0.015 -> 0.02
        self.assertEqual(book.realized(), Decimal("0.02"))
        self.assertEqual(str(book.realized()), "0.02")

    def test_realized_starts_at_zero(self):
        self.assertEqual(str(FifoBook().realized()), "0.00")

    def test_insufficient_changes_nothing(self):
        book = FifoBook()
        book.buy(2, "1")
        with self.assertRaisesRegex(ValueError, "^insufficient"):
            book.sell(3, "2")
        self.assertEqual(book.holdings(), 2)
        self.assertEqual(book.lots(), [(2, "1")])
        self.assertEqual(book.realized(), Decimal("0"))

    def test_lot_keeps_its_original_price_string(self):
        book = FifoBook()
        book.buy(4, "12.50")
        book.sell(1, "13")
        self.assertEqual(book.lots(), [(3, "12.50")])

    def test_lots_returns_a_copy(self):
        book = FifoBook()
        book.buy(1, "1")
        book.lots().clear()
        self.assertEqual(book.lots(), [(1, "1")])

    def test_cost_basis(self):
        book = FifoBook()
        book.buy(3, "0.3333")
        book.buy(1, "0.0050")
        self.assertEqual(book.cost_basis(), Decimal("1.00"))  # 0.9999 + 0.005 = 1.0049
        book.sell(3, "1")
        self.assertEqual(book.cost_basis(), Decimal("0.00"))  # 0.005 -> 0.00

    def test_price_validation(self):
        book = FifoBook()
        for bad in ("1.", ".5", "-1", "1.23456", "1e3", " 1", "１", "1,5", ""):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    book.buy(1, bad)
        with self.assertRaises(TypeError):
            book.buy(1, 1.5)
        with self.assertRaises(TypeError):
            book.buy(1, Decimal("1.5"))
        self.assertEqual(book.holdings(), 0)

    def test_qty_validation(self):
        book = FifoBook()
        with self.assertRaises(TypeError):
            book.buy(True, "1")
        with self.assertRaises(TypeError):
            book.buy(1.0, "1")
        with self.assertRaises(ValueError):
            book.buy(0, "1")
        book.buy(1, "1")
        with self.assertRaises(ValueError):
            book.sell(-1, "1")
        self.assertEqual(book.holdings(), 1)

    def test_sell_everything_then_buy_again(self):
        book = FifoBook()
        book.buy(2, "3")
        book.sell(2, "4")
        self.assertEqual(book.lots(), [])
        book.buy(1, "2")
        self.assertEqual(book.sell(1, "2"), Decimal("0.00"))
        self.assertEqual(book.realized(), Decimal("2.00"))


class TestPerformance(unittest.TestCase):
    def test_many_small_lots(self):
        rng = random.Random(5)
        book = FifoBook()
        started = time.perf_counter()
        for _ in range(150000):
            book.buy(1, f"{rng.randint(100, 200)}.{rng.randint(0, 9999):04d}")
        for _ in range(50000):
            book.sell(3, "150")
        elapsed = time.perf_counter() - started
        self.assertEqual(book.holdings(), 0)
        self.assertEqual(book.lots(), [])
        self.assertLess(elapsed, 4.0)
