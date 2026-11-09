import re
from decimal import Decimal

_FORMAT = re.compile(r"[0-9]+(?:\.[0-9]{1,2})?")
_FEE = Decimal("1.50")
_CENT = Decimal("0.01")


class InsufficientFunds(Exception):
    pass


def _parse(value, allow_zero=False):
    if not isinstance(value, str):
        raise TypeError("amounts must be strings")
    if not _FORMAT.fullmatch(value):
        raise ValueError(f"invalid amount: {value!r}")
    amount = Decimal(value)
    if amount == 0 and not allow_zero:
        raise ValueError("amount must be positive")
    return amount


def _text(amount):
    return f"{amount.quantize(_CENT):.2f}"


class Ledger:
    def __init__(self, overdraft_limit="0.00"):
        self._limit = _parse(overdraft_limit, allow_zero=True)
        self._balance = Decimal("0.00")
        self._history = []

    def deposit(self, amount):
        value = _parse(amount)
        self._balance += value
        self._history.append(("deposit", _text(value)))

    def withdraw(self, amount):
        value = _parse(amount)
        if self._balance - value < -self._limit:
            raise InsufficientFunds(f"withdrawal of {_text(value)} exceeds the overdraft limit")
        self._balance -= value
        self._history.append(("withdraw", _text(value)))
        if self._balance < 0:
            self._balance -= _FEE
            self._history.append(("fee", _text(_FEE)))

    def balance(self):
        return _text(self._balance)

    def history(self):
        return list(self._history)
