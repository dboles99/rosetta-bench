def differing_keys(a, b):
    return sorted(k for k in set(a) | set(b) if str(a.get(k)) != str(b.get(k)))
