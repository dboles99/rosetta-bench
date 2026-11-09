def rle_encode(s):
    out = []
    i = 0
    while i < len(s):
        ch = s[i]
        j = i
        while j < len(s) and s[j] == ch:
            j += 1
        run = j - i
        if ch == "~" or run >= 4:
            out.append(f"~{ch}{run};")
        else:
            out.append(ch * run)
        i = j
    return "".join(out)


def rle_decode(s):
    out = []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch != "~":
            out.append(ch)
            i += 1
            continue
        if i + 1 >= len(s):
            raise ValueError("dangling escape")
        target = s[i + 1]
        j = i + 2
        while j < len(s) and s[j].isascii() and s[j].isdigit():
            j += 1
        digits = s[i + 2:j]
        if not digits or j >= len(s) or s[j] != ";":
            raise ValueError("malformed run")
        if digits[0] == "0":
            raise ValueError("bad count")
        out.append(target * int(digits))
        i = j + 1
    return "".join(out)
