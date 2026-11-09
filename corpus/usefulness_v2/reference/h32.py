def exact_label(x):
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        raise TypeError("exact_label needs an int or float")
    value = float(x)
    if value == 0:
        return "0"
    text = repr(value)
    return text[:-2] if text.endswith(".0") else text
