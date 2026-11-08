"""Mask personal or secret-looking values before state leaves the machine.

The same original always maps to the same placeholder within one Masker, so the
masked state stays deterministic for replay. The originals stay in memory only and
are used to check that no output file contains them."""
import re

_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_SECRET = re.compile(r"\b(?:sk|pk|rk)-[A-Za-z0-9_\-]{16,}\b")
_PHONE = re.compile(r"(?<![\w.])\+?\d[\d\s().\-]{7,}\d(?![\w.])")
_MIN_PHONE_DIGITS = 9
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class Masker:
    def __init__(self, extra_literals: tuple[str, ...] = ()):
        self._extra = tuple(literal for literal in extra_literals if literal)
        self._placeholders: dict[str, str] = {}
        self._counts: dict[str, int] = {}

    def _placeholder(self, kind: str, original: str) -> str:
        if original not in self._placeholders:
            self._counts[kind] = self._counts.get(kind, 0) + 1
            self._placeholders[original] = f"<{kind}{self._counts[kind]}>"
        return self._placeholders[original]

    def _phone(self, match: re.Match) -> str:
        text = match.group(0)
        digits = sum(ch.isdigit() for ch in text)
        if digits < _MIN_PHONE_DIGITS or _DATE.match(text.strip()):
            return text
        return self._placeholder("phone", text)

    def mask_text(self, text: str) -> str:
        for literal in self._extra:
            if literal in text:
                text = text.replace(literal, self._placeholder("literal", literal))
        text = _SECRET.sub(lambda m: self._placeholder("secret", m.group(0)), text)
        text = _EMAIL.sub(lambda m: self._placeholder("email", m.group(0)), text)
        return _PHONE.sub(self._phone, text)

    def mask_value(self, value):
        if isinstance(value, str):
            return self.mask_text(value)
        if isinstance(value, dict):
            return {key: self.mask_value(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [self.mask_value(item) for item in value]
        return value

    @property
    def originals(self) -> tuple[str, ...]:
        return tuple(self._placeholders)
