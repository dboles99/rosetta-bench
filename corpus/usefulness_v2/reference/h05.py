from fractions import Fraction


def _tokenize(expr):
    tokens = []
    i = 0
    while i < len(expr):
        ch = expr[i]
        if ch in " \t":
            i += 1
        elif ch.isascii() and ch.isdigit():
            j = i
            while j < len(expr) and expr[j].isascii() and expr[j].isdigit():
                j += 1
            tokens.append(("num", int(expr[i:j])))
            i = j
        elif ch in "+-*/^()":
            tokens.append(("op", ch))
            i += 1
        else:
            raise ValueError(f"bad character {ch!r}")
    return tokens


class _Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def take(self, value=None):
        tok = self.peek()
        if tok is None or (value is not None and tok != ("op", value)):
            raise ValueError("unexpected end or token")
        self.pos += 1
        return tok

    def expr(self):
        value = self.term()
        while self.peek() in (("op", "+"), ("op", "-")):
            op = self.take()[1]
            rhs = self.term()
            value = value + rhs if op == "+" else value - rhs
        return value

    def term(self):
        value = self.unary()
        while self.peek() in (("op", "*"), ("op", "/")):
            op = self.take()[1]
            rhs = self.unary()
            if op == "*":
                value = value * rhs
            else:
                if rhs == 0:
                    raise ZeroDivisionError("division by zero")
                value = value / rhs
        return value

    def unary(self):
        if self.peek() == ("op", "-"):
            self.take()
            return -self.unary()
        return self.power()

    def power(self):
        base = self.atom()
        if self.peek() == ("op", "^"):
            self.take()
            exponent = self.unary()
            if exponent.denominator != 1:
                raise ValueError("non-integer exponent")
            if base == 0 and exponent < 0:
                raise ZeroDivisionError("zero to a negative power")
            return base ** int(exponent)
        return base

    def atom(self):
        tok = self.peek()
        if tok is None:
            raise ValueError("unexpected end")
        if tok[0] == "num":
            self.pos += 1
            return Fraction(tok[1])
        if tok == ("op", "("):
            self.take()
            value = self.expr()
            self.take(")")
            return value
        raise ValueError(f"unexpected token {tok[1]!r}")


def evaluate(expr):
    parser = _Parser(_tokenize(expr))
    if not parser.tokens:
        raise ValueError("empty expression")
    value = parser.expr()
    if parser.peek() is not None:
        raise ValueError("trailing tokens")
    return int(value) if value.denominator == 1 else value
