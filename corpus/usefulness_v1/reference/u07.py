import random

def family_split(families, fraction, seed):
    names = sorted(set(families))
    random.Random(seed).shuffle(names)
    cut = round(len(names) * fraction)
    return {name: ("calibration" if index < cut else "held_out") for index, name in enumerate(names)}
