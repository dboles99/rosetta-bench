import random
import time
import unittest
from solution import assign_rooms, busiest_room


def brute(meetings, k):
    end = [None] * k
    order = sorted(range(len(meetings)), key=lambda i: (meetings[i][0], i))
    out = [None] * len(meetings)
    for i in order:
        s, e = meetings[i]
        free = [r for r in range(k) if end[r] is None or end[r] <= s]
        if free:
            room, start = min(free), s
        else:
            room = min(range(k), key=lambda r: (end[r], r))
            start = end[room]
        end[room] = start + (e - s)
        out[i] = (room, start, start + (e - s))
    return out


class TestAssignRooms(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(assign_rooms([(0, 10), (1, 5), (2, 7)], 2), [(0, 0, 10), (1, 1, 5), (1, 5, 10)])

    def test_output_in_input_order(self):
        self.assertEqual(assign_rooms([(5, 6), (0, 3)], 1), [(0, 5, 6), (0, 0, 3)])

    def test_same_start_ties_by_index(self):
        self.assertEqual(assign_rooms([(0, 4), (0, 2), (0, 3)], 2), [(0, 0, 4), (1, 0, 2), (1, 2, 5)])

    def test_half_open_touching_is_free(self):
        self.assertEqual(assign_rooms([(0, 5), (5, 8)], 1), [(0, 0, 5), (0, 5, 8)])

    def test_smallest_free_room_not_most_recent(self):
        # room 1 frees at 3, room 0 frees at 4; at time 6 both free -> room 0
        self.assertEqual(assign_rooms([(0, 4), (0, 3), (6, 7)], 2), [(0, 0, 4), (1, 0, 3), (0, 6, 7)])

    def test_delay_takes_earliest_end_then_smallest_room(self):
        self.assertEqual(assign_rooms([(0, 5), (0, 5), (1, 3)], 2), [(0, 0, 5), (1, 0, 5), (0, 5, 7)])

    def test_delayed_meetings_keep_order(self):
        self.assertEqual(assign_rooms([(0, 10), (1, 2), (2, 3)], 1), [(0, 0, 10), (0, 10, 11), (0, 11, 12)])

    def test_empty(self):
        self.assertEqual(assign_rooms([], 3), [])

    def test_errors(self):
        for meetings, k in (([(0, 1)], 0), ([(0, 1)], True), ([(2, 2)], 1), ([(3, 1)], 1), ([(0.0, 1)], 1)):
            with self.subTest(meetings=meetings, k=k):
                with self.assertRaises(ValueError):
                    assign_rooms(meetings, k)

    def test_input_not_mutated(self):
        meetings = [(3, 4), (0, 2)]
        assign_rooms(meetings, 1)
        self.assertEqual(meetings, [(3, 4), (0, 2)])

    def test_random_against_spec(self):
        rng = random.Random(4)
        for _ in range(300):
            k = rng.randint(1, 4)
            meetings = []
            for _ in range(rng.randint(0, 12)):
                s = rng.randint(0, 20)
                meetings.append((s, s + rng.randint(1, 6)))
            self.assertEqual(assign_rooms(meetings, k), brute(meetings, k))


class TestBusiest(unittest.TestCase):
    def test_busiest(self):
        self.assertEqual(busiest_room([(0, 10), (1, 5), (2, 7), (3, 4)], 3), 1)

    def test_tie_smallest_room(self):
        self.assertEqual(busiest_room([(0, 1), (0, 1)], 2), 0)

    def test_empty_is_room_zero(self):
        self.assertEqual(busiest_room([], 5), 0)


class TestPerformance(unittest.TestCase):
    def test_large(self):
        rng = random.Random(7)
        meetings = []
        for _ in range(200000):
            s = rng.randint(0, 10_000_000)
            meetings.append((s, s + rng.randint(1, 100_000)))
        started = time.perf_counter()
        result = assign_rooms(meetings, 2000)
        elapsed = time.perf_counter() - started
        self.assertEqual(len(result), 200000)
        self.assertTrue(all(0 <= r < 2000 and e - s == m[1] - m[0] for (r, s, e), m in zip(result, meetings)))
        self.assertLess(elapsed, 4.5)
