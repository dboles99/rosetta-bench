import re

_BLOCK = re.compile(r"```([A-Za-z0-9_+\-]*)[ \t]*\r?\n(.*?)```", re.DOTALL)
_NOT_APPLICABLE = re.compile(r"\s*NOT_A_[A-Z_]+_TASK\s*")


def extract_code(text: str | None) -> str | None:
    """The last ```python block, else the last unlabelled block, else None."""
    if not text:
        return None
    blocks = _BLOCK.findall(text)
    python = [body for lang, body in blocks if lang.lower() in ("python", "py", "python3")]
    plain = [body for lang, body in blocks if lang == ""]
    chosen = python[-1] if python else (plain[-1] if plain else None)
    if chosen is None:
        return None
    return chosen if chosen.endswith("\n") else chosen + "\n"


def says_not_applicable(text: str | None) -> bool:
    return bool(text) and _NOT_APPLICABLE.fullmatch(text) is not None
