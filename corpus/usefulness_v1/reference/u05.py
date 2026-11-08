import re

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

def mask_emails(text):
    seen = {}
    def replace(match):
        address = match.group(0)
        if address not in seen:
            seen[address] = f"<email{len(seen) + 1}>"
        return seen[address]
    return _EMAIL.sub(replace, text)
