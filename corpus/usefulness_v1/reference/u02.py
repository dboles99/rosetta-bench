def parse_packet(text):
    schema_ver = None
    fields = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key == "SCHEMA_VER":
            schema_ver = value
        else:
            fields[key] = value
    if schema_ver is None:
        raise ValueError("missing SCHEMA_VER")
    return schema_ver, fields
