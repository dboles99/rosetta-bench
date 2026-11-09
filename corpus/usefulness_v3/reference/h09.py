import re
from collections import deque
from decimal import ROUND_HALF_EVEN, Decimal

_PRICE = re.compile(r"[0-9]+(?:\.[0-9]{1,4})?")
_CENT = Decimal("0.01")


def _qty(qty):
    if isinstance(qty, bool) or not isinstance(qty, int):
        raise TypeError("qty must be int")
    if qty <= 0:
        raise ValueError("qty must be positive")
    return qty


def _price(price):
    if not isinstance(price, str):
        raise TypeError("price must be str")
    if not _PRICE.fullmatch(price):
        raise ValueError(f"invalid price: {price}")
    return Decimal(price)


class FifoBook:
    def __init__(self):
        self._lots = deque()  # [qty, Decimal price, original string]
        self._holdings = 0
        self._realized = Decimal("0.00")

    def buy(self, qty, price):
        qty, value = _qty(qty), _price(price)
        self._lots.append([qty, value, price])
        self._holdings += qty

    def sell(self, qty, price):
        qty, value = _qty(qty), _price(price)
        if qty > self._holdings:
            raise ValueError(f"insufficient holdings: {self._holdings} < {qty}")
        profit = Decimal(0)
        remaining = qty
        while remaining:
            lot = self._lots[0]
            take = min(remaining, lot[0])
            profit += (value - lot[1]) * take
            lot[0] -= take
            remaining -= take
            if lot[0] == 0:
                self._lots.popleft()
        self._holdings -= qty
        rounded = profit.quantize(_CENT, rounding=ROUND_HALF_EVEN)
        self._realized += rounded
        return rounded

    def realized(self):
        return self._realized.quantize(_CENT)

    def holdings(self):
        return self._holdings

    def lots(self):
        return [(lot[0], lot[2]) for lot in self._lots]

    def cost_basis(self):
        total = sum((lot[1] * lot[0] for lot in self._lots), Decimal(0))
        return total.quantize(_CENT, rounding=ROUND_HALF_EVEN)
