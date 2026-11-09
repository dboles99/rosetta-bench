import re


def _class(content, negate):
    parts = []
    i = 0
    while i < len(content):
        if i + 2 < len(content) and content[i + 1] == "-":
            parts.append(f"{re.escape(content[i])}-{re.escape(content[i + 2])}")
            i += 3
        else:
            parts.append(re.escape(content[i]))
            i += 1
    body = "".join(parts)
    return f"[^/{body}]" if negate else f"(?!/)[{body}]"


def glob_to_regex(pattern):
    out = []
    i, n = 0, len(pattern)
    while i < n:
        ch = pattern[i]
        if ch == "\\":
            if i + 1 < n:
                out.append(re.escape(pattern[i + 1]))
                i += 2
            else:
                out.append(re.escape("\\"))
                i += 1
        elif ch == "*":
            j = i
            while j < n and pattern[j] == "*":
                j += 1
            segment_start = i == 0 or pattern[i - 1] == "/"
            if j - i == 2 and segment_start and j == n:
                out.append(".*")
                i = j
            elif j - i == 2 and segment_start and pattern[j] == "/":
                out.append("(?:[^/]*/)*")
                i = j + 1
            else:
                out.append("[^/]*")
                i = j
        elif ch == "?":
            out.append("[^/]")
            i += 1
        elif ch == "[":
            j = i + 1
            negate = j < n and pattern[j] == "!"
            if negate:
                j += 1
            start = j
            if j < n and pattern[j] == "]":
                j += 1
            close = pattern.find("]", j)
            if close == -1:
                out.append(re.escape("["))
                i += 1
            else:
                out.append(_class(pattern[start:close], negate))
                i = close + 1
        else:
            out.append(re.escape(ch))
            i += 1
    return "".join(out)


def glob_match(pattern, path):
    return re.fullmatch(glob_to_regex(pattern), path) is not None
