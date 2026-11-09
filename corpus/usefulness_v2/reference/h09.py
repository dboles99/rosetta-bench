import unicodedata


def _keep(ch):
    return ("a" <= ch <= "z") or ("0" <= ch <= "9") or ("一" <= ch <= "鿿")


def slugify(text, max_len=50):
    if max_len < 1:
        raise ValueError("max_len must be >= 1")
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in decomposed if unicodedata.combining(ch) == 0).lower()
    pieces = []
    for ch in stripped:
        if _keep(ch):
            pieces.append(ch)
        elif pieces and pieces[-1] != "-":
            pieces.append("-")
    slug = "".join(pieces).strip("-")
    slug = slug[:max_len].rstrip("-")
    return slug or "n-a"
