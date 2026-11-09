import unittest
from solution import UserIndex


class TestUserIndex(unittest.TestCase):
    def setUp(self):
        self.alice = {"id": 1, "name": "alice"}
        self.bob = {"id": 2, "name": "bob"}
        self.alice2 = {"id": 1, "name": "alice-duplicate"}
        self.users = [self.alice, self.bob, self.alice2]

    def test_identity(self):
        self.assertIs(UserIndex(self.users).get(2), self.bob)

    def test_first_duplicate_wins(self):
        self.assertIs(UserIndex(self.users).get(1), self.alice)

    def test_unknown(self):
        self.assertIsNone(UserIndex(self.users).get(99))

    def test_len_counts_distinct_ids(self):
        self.assertEqual(len(UserIndex(self.users)), 2)
        self.assertEqual(len(UserIndex([])), 0)

    def test_no_mutation(self):
        before = [dict(u) for u in self.users]
        UserIndex(self.users).get(1)
        self.assertEqual(self.users, before)
        self.assertEqual(len(self.users), 3)

    def test_string_ids(self):
        carol = {"id": "c", "name": "carol"}
        self.assertIs(UserIndex([carol]).get("c"), carol)
