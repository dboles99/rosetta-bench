import re

_BULLET = re.compile(r"^\s*(?:[-*\u2022]|\d+[.)])\s+\S")

def bullet_count(text):
    return sum(1 for line in text.splitlines() if _BULLET.match(line))
