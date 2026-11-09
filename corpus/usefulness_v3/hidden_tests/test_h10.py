import unittest

from solution import Scheduler


class SchedulerTests(unittest.TestCase):
    def test_highest_priority_first(self):
        s = Scheduler()
        s.add("low", 1)
        s.add("high", 5)
        s.add("mid", 3)
        self.assertEqual([s.next(), s.next(), s.next()], ["high", "mid", "low"])
        self.assertIsNone(s.next())

    def test_ties_break_by_insertion_order(self):
        s = Scheduler()
        s.add("b", 2)
        s.add("a", 2)
        s.add("c", 2)
        self.assertEqual([s.next(), s.next(), s.next()], ["b", "a", "c"])

    def test_negative_priorities(self):
        s = Scheduler()
        s.add("x", -5)
        s.add("y", -1)
        self.assertEqual(s.next(), "y")

    def test_dependency_must_complete_not_just_start(self):
        s = Scheduler()
        s.add("build", 1)
        s.add("test", 10, after=["build"])
        self.assertEqual(s.next(), "build")
        self.assertIsNone(s.next())
        s.complete("build")
        self.assertEqual(s.next(), "test")

    def test_unknown_dependency_raises_key_error(self):
        s = Scheduler()
        with self.assertRaises(KeyError):
            s.add("deploy", 1, after=["build"])
        s.add("build", 1)
        s.add("deploy", 1, after=["build"])

    def test_duplicate_name_raises_value_error(self):
        s = Scheduler()
        s.add("a", 1)
        with self.assertRaises(ValueError):
            s.add("a", 2)

    def test_complete_rules(self):
        s = Scheduler()
        s.add("a", 1)
        with self.assertRaises(ValueError):
            s.complete("a")
        self.assertEqual(s.next(), "a")
        s.complete("a")
        with self.assertRaises(ValueError):
            s.complete("a")
        with self.assertRaises(KeyError):
            s.complete("missing")

    def test_remaining_counts_running_tasks(self):
        s = Scheduler()
        s.add("a", 1)
        s.add("b", 1)
        self.assertEqual(s.remaining(), 2)
        s.next()
        self.assertEqual(s.remaining(), 2)
        s.complete("a")
        self.assertEqual(s.remaining(), 1)

    def test_lower_priority_ready_task_runs_while_higher_is_blocked(self):
        s = Scheduler()
        s.add("base", 1)
        s.add("urgent", 100, after=["base"])
        s.add("side", 0)
        self.assertEqual(s.next(), "base")
        self.assertEqual(s.next(), "side")
        s.complete("base")
        self.assertEqual(s.next(), "urgent")

    def test_multiple_dependencies(self):
        s = Scheduler()
        s.add("a", 1)
        s.add("b", 1)
        s.add("c", 9, after=("a", "b"))
        first = s.next()
        s.complete(first)
        self.assertEqual(s.next(), "b")
        self.assertIsNone(s.next())
        s.complete("b")
        self.assertEqual(s.next(), "c")


if __name__ == "__main__":
    unittest.main()
