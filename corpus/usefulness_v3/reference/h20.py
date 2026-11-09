import re

_TOKEN = re.compile(r"\\\\|\\\{\{|\{\{(.*?)\}\}|\{\{|[^\\{]+|[\\{]", re.S)
_KEY = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*")
_MISSING = object()


def _lookup(values, key):
    current = values
    for part in key.split("."):
        if not isinstance(current, dict) or part not in current:
            return _MISSING
        current = current[part]
    return _MISSING if current is None else current


def _format(value):
    if value is True:
        return "true"
    if value is False:
        return "false"
    return str(value)


def render(template, values):
    out = []
    for match in _TOKEN.finditer(template):
        text = match.group(0)
        if text == "\\\\":
            out.append("\\")
        elif text == "\\{{":
            out.append("{{")
        elif text == "{{":
            raise ValueError(f"unclosed placeholder at {match.start()}")
        elif match.group(1) is not None:
            content = match.group(1)
            key_part, bar, fallback = content.partition("|")
            key = key_part.strip(" ")
            if not _KEY.fullmatch(key):
                raise ValueError(f"bad key: {key}")
            value = _lookup(values, key)
            if value is _MISSING:
                if not bar:
                    raise KeyError(f"missing: {key}")
                out.append(fallback.strip(" "))
            else:
                out.append(_format(value))
        else:
            out.append(text)
    return "".join(out)
