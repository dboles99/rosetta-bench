import random
import time
import unittest
from solution import schedule, waiting_times


def brute(tasks):
    left = set(range(len(tasks)))
    now, out = 0, []
    while left:
        ready = [i for i in left if tasks[i][0] <= now]
        if not ready:
            now = min(tasks[i][0] for i in left)
            continue
        i = min(ready, key=lambda j: (-tasks[j][2], tasks[j][1], j))
        out.append((i, now, now + tasks[i][1]))
        now += tasks[i][1]
        left.remove(i)
    return out


class TestSchedule(unittest.TestCase):
    def test_priority_first(self):
        tasks = [(0, 5, 1), (1, 2, 9), (1, 3, 4)]
        self.assertEqual(schedule(tasks), [(0, 0, 5), (1, 5, 7), (2, 7, 10)])

    def test_tie_shorter_then_index(self):
        tasks = [(0, 1, 0), (0, 4, 3), (0, 2, 3), (0, 2, 3)]
        self.assertEqual(schedule(tasks), [(2, 0, 2), (3, 2, 4), (1, 4, 8), (0, 8, 9)])

    def test_idle_jump(self):
        self.assertEqual(schedule([(10, 1, 0), (3, 2, 0)]), [(1, 3, 5), (0, 10, 11)])

    def test_task_enqueued_exactly_at_finish_is_available(self):
        tasks = [(0, 4, 0), (4, 1, 1), (2, 1, 0)]
        self.assertEqual(schedule(tasks), [(0, 0, 4), (1, 4, 5), (2, 5, 6)])

    def test_non_preemptive(self):
        tasks = [(0, 10, 0), (1, 1, 100)]
        self.assertEqual(schedule(tasks), [(0, 0, 10), (1, 10, 11)])

    def test_zero_duration(self):
        tasks = [(0, 0, 1), (0, 3, 0), (0, 0, 2)]
        self.assertEqual(schedule(tasks), [(2, 0, 0), (0, 0, 0), (1, 0, 3)])

    def test_negative_priority(self):
        self.assertEqual(schedule([(0, 1, -5), (0, 1, -1)]), [(1, 0, 1), (0, 1, 2)])

    def test_empty(self):
        self.assertEqual(schedule([]), [])
        self.assertEqual(waiting_times([]), [])

    def test_errors(self):
        with self.assertRaises(ValueError):
            schedule([(-1, 1, 0)])
        with self.assertRaises(ValueError):
            schedule([(0, -1, 0)])
        with self.assertRaises(TypeError):
            schedule([(0, 1, True)])
        with self.assertRaises(TypeError):
            schedule([(0, 1.0, 0)])

    def test_waiting_times_in_input_order(self):
        tasks = [(0, 5, 1), (1, 2, 9), (1, 3, 4)]
        self.assertEqual(waiting_times(tasks), [0, 4, 6])

    def test_random_against_brute(self):
        rng = random.Random(11)
        for _ in range(300):
            tasks = [(rng.randint(0, 15), rng.randint(0, 4), rng.randint(-2, 2)) for _ in range(rng.randint(0, 10))]
            self.assertEqual(schedule(tasks), brute(tasks))


class TestPerformance(unittest.TestCase):
    def test_large(self):
        rng = random.Random(12)
        tasks = [(rng.randint(0, 1000), rng.randint(0, 50), rng.randint(0, 1000)) for _ in range(200000)]
        started = time.perf_counter()
        result = schedule(tasks)
        elapsed = time.perf_counter() - started
        self.assertEqual(sorted(i for i, _, _ in result), list(range(200000)))
        self.assertEqual(result[-1][2], sum(t[1] for t in tasks) + min(t[0] for t in tasks))
        self.assertLess(elapsed, 5.0)
