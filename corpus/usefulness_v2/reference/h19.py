import copy


def _tokens(pointer):
    if not isinstance(pointer, str):
        raise ValueError("invalid pointer")
    if pointer == "":
        return []
    if not pointer.startswith("/"):
        raise ValueError("invalid pointer: must start with '/'")
    tokens = []
    for raw in pointer[1:].split("/"):
        buf, i = [], 0
        while i < len(raw):
            ch = raw[i]
            if ch == "~":
                nxt = raw[i + 1:i + 2]
                if nxt == "0":
                    buf.append("~")
                elif nxt == "1":
                    buf.append("/")
                else:
                    raise ValueError("invalid pointer: bad escape")
                i += 2
            else:
                buf.append(ch)
                i += 1
        tokens.append("".join(buf))
    return tokens


def _is_index(token):
    return token == "0" or (token.isascii() and token.isdigit() and token[0] != "0")


def _step(current, token):
    if isinstance(current, dict):
        if token not in current:
            raise KeyError(token)
        return current[token]
    if isinstance(current, list):
        if not _is_index(token) or int(token) >= len(current):
            raise KeyError(token)
        return current[int(token)]
    raise KeyError(token)


def resolve(doc, pointer):
    current = doc
    for token in _tokens(pointer):
        current = _step(current, token)
    return current


def set_value(doc, pointer, value):
    tokens = _tokens(pointer)
    if not tokens:
        return value
    new_doc = copy.deepcopy(doc)
    parent = new_doc
    for token in tokens[:-1]:
        parent = _step(parent, token)
    last = tokens[-1]
    if isinstance(parent, dict):
        parent[last] = value
    elif isinstance(parent, list):
        if last == "-":
            parent.append(value)
        elif _is_index(last) and int(last) < len(parent):
            parent[int(last)] = value
        elif _is_index(last) and int(last) == len(parent):
            parent.append(value)
        else:
            raise KeyError(last)
    else:
        raise KeyError(last)
    return new_doc


def escape_token(token):
    return token.replace("~", "~0").replace("/", "~1")
