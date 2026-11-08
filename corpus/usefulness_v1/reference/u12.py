def coerce_numeric(fields, schema):
    properties = schema.get("properties", {})
    result = dict(fields)
    for key, value in fields.items():
        if key not in properties or not isinstance(value, str):
            continue
        kind = properties[key].get("type")
        try:
            if kind == "integer":
                result[key] = int(value)
            elif kind == "number":
                result[key] = float(value)
        except ValueError:
            pass
    return result
