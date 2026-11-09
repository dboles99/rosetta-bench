def parse_port(s):
    text = s.strip()
    if not text or not all("0" <= ch <= "9" for ch in text) or (len(text) > 1 and text[0] == "0"):
        raise ValueError("invalid port: " + s)
    n = int(text)
    if not 1 <= n <= 65535:
        raise ValueError("port out of range: " + s)
    return n
