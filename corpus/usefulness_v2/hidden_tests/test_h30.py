import unittest
from solution import fetch_with_retry


def scripted(results):
    calls = []

    def fetch():
        calls.append(1)
        item = results[len(calls) - 1]
        if isinstance(item, BaseException):
            raise item
        return item
    return fetch, calls


class TestRetry(unittest.TestCase):
    def setUp(self):
        self.sleeps = []

    def test_first_try(self):
        fetch, calls = scripted(["ok"])
        self.assertEqual(fetch_with_retry(fetch, self.sleeps.append), "ok")
        self.assertEqual(self.sleeps, [])

    def test_recovers(self):
        fetch, calls = scripted([ConnectionError(), ConnectionError(), "ok"])
        self.assertEqual(fetch_with_retry(fetch, self.sleeps.append), "ok")
        self.assertEqual(self.sleeps, [1, 2])

    def test_gives_up_with_last_error(self):
        last = ConnectionError("third")
        fetch, calls = scripted([ConnectionError("1"), ConnectionError("2"), last, "never"])
        with self.assertRaises(ConnectionError) as caught:
            fetch_with_retry(fetch, self.sleeps.append)
        self.assertIs(caught.exception, last)
        self.assertEqual(len(calls), 3)
        self.assertEqual(self.sleeps, [1, 2])

    def test_single_attempt(self):
        fetch, calls = scripted([ConnectionError()])
        with self.assertRaises(ConnectionError):
            fetch_with_retry(fetch, self.sleeps.append, max_attempts=1)
        self.assertEqual(self.sleeps, [])

    def test_other_errors_propagate(self):
        fetch, calls = scripted([KeyError("x"), "ok"])
        with self.assertRaises(KeyError):
            fetch_with_retry(fetch, self.sleeps.append)
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.sleeps, [])

    def test_subclass_retried(self):
        fetch, calls = scripted([ConnectionResetError(), "ok"])
        self.assertEqual(fetch_with_retry(fetch, self.sleeps.append), "ok")

    def test_cap(self):
        fetch, calls = scripted([ConnectionError()] * 8)
        with self.assertRaises(ConnectionError):
            fetch_with_retry(fetch, self.sleeps.append, max_attempts=8, max_delay=5)
        self.assertEqual(self.sleeps, [1, 2, 4, 5, 5, 5, 5])

    def test_bad_attempts(self):
        fetch, calls = scripted(["ok"])
        with self.assertRaises(ValueError):
            fetch_with_retry(fetch, self.sleeps.append, max_attempts=0)
        self.assertEqual(calls, [])
