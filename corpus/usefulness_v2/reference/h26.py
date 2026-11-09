class ConflictError(ValueError):
    def __init__(self, keys):
        self.keys = list(keys)
        super().__init__("conflicting keys: " + ", ".join(self.keys))


def merge_configs(base, override):
    conflicts = sorted(k for k in base.keys() & override.keys() if base[k] != override[k])
    if conflicts:
        raise ConflictError(conflicts)
    merged = dict(base)
    merged.update(override)
    return merged
