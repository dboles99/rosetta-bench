def parse_ini(text):
    result = {}
    section = None
    current = None
    for number, raw in enumerate(text.split("\n"), 1):
        line = raw.rstrip("\r")
        stripped = line.strip()
        if not stripped:
            current = None
            continue
        if stripped[0] in ";#":
            continue
        if line[0] in " \t":
            if current is None:
                raise ValueError(f"line {number}: unexpected continuation")
            sec, key = current
            value = result[sec][key]
            result[sec][key] = f"{value} {stripped}" if value else stripped
            continue
        current = None
        if stripped.startswith("[") and stripped.endswith("]"):
            section = stripped[1:-1].strip().lower()
            result.setdefault(section, {})
            continue
        if "=" not in stripped:
            raise ValueError(f"line {number}: expected key = value")
        key, _, value = stripped.partition("=")
        key = key.strip().lower()
        if not key:
            raise ValueError(f"line {number}: empty key")
        sec = "" if section is None else section
        result.setdefault(sec, {})
        if key in result[sec]:
            raise ValueError(f"duplicate key: {sec}.{key}")
        result[sec][key] = value.strip()
        current = (sec, key)
    for values in result.values():
        for key, value in values.items():
            if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
                values[key] = value[1:-1]
    return result
