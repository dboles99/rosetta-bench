def wrap_text(text, width):
    if isinstance(width, bool) or not isinstance(width, int) or width < 2:
        raise ValueError("width must be an int >= 2")
    lines = []
    current = ""
    for word in text.split():
        if len(word) > width:
            if current:
                lines.append(current)
            while len(word) > width:
                lines.append(word[:width - 1] + "-")
                word = word[width - 1:]
            current = word
        elif not current:
            current = word
        elif len(current) + 1 + len(word) <= width:
            current += " " + word
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines
