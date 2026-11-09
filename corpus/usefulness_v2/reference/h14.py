import functools
import re

_NUM = r"(0|[1-9][0-9]*)"
_IDS = r"[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*"
_VERSION = re.compile(rf"[vV]?{_NUM}\.{_NUM}\.{_NUM}(?:-({_IDS}))?(?:\+({_IDS}))?")


def parse_version(text):
    match = _VERSION.fullmatch(text) if isinstance(text, str) else None
    if match is None:
        raise ValueError(f"invalid version: {text!r}")
    major, minor, patch, pre, build = match.groups()
    identifiers = []
    if pre is not None:
        for ident in pre.split("."):
            if ident.isdigit():
                if len(ident) > 1 and ident[0] == "0":
                    raise ValueError(f"invalid version: {text!r}")
                identifiers.append(int(ident))
            else:
                identifiers.append(ident)
    return (int(major), int(minor), int(patch), tuple(identifiers), build)


def _cmp(a, b):
    return (a > b) - (a < b)


def compare_versions(a, b):
    pa, pb = parse_version(a), parse_version(b)
    result = _cmp(pa[:3], pb[:3])
    if result:
        return result
    xa, xb = pa[3], pb[3]
    if not xa and not xb:
        return 0
    if not xa:
        return 1
    if not xb:
        return -1
    for ia, ib in zip(xa, xb):
        if ia == ib:
            continue
        a_num, b_num = isinstance(ia, int), isinstance(ib, int)
        if a_num and b_num:
            return _cmp(ia, ib)
        if a_num:
            return -1
        if b_num:
            return 1
        return _cmp(ia, ib)
    return _cmp(len(xa), len(xb))


def sort_versions(versions):
    return sorted(versions, key=functools.cmp_to_key(compare_versions))
