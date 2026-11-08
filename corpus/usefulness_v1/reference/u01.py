def canonical_packet(schema_ver, fields):
    lines = [f"SCHEMA_VER={schema_ver}"]
    for key in sorted(fields):
        value = fields[key]
        lines.append(f"{key}={value:.2f}" if isinstance(value, float) else f"{key}={value}")
    return "\n".join(lines) + "\n"
