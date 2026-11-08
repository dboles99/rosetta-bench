import unittest
from solution import family_split


class AcceptanceTests(unittest.TestCase):
    def expected(self, families, fraction, seed):
        import random
        names = sorted(set(families))
        random.Random(seed).shuffle(names)
        cut = round(len(names) * fraction)
        return {n: ("calibration" if i < cut else "held_out") for i, n in enumerate(names)}
    def test_matches_spec(self):
        fams = [f"f{i:02d}" for i in range(10)]
        self.assertEqual(family_split(fams, 0.4, 7), self.expected(fams, 0.4, 7))
    def test_duplicates_removed(self):
        self.assertEqual(len(family_split(["a", "a", "b"], 0.5, 1)), 2)
    def test_counts(self):
        result = family_split([f"f{i}" for i in range(5)], 0.4, 3)
        self.assertEqual(sum(v == "calibration" for v in result.values()), 2)
