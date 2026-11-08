"""Sandbox tests. Unit tests check the docker command offline. Tests marked docker_live run
real containers and only when ROSETTA_BENCH_DOCKER=1 (they need Docker and python:3.12-slim)."""
import os
import subprocess

import pytest

from rosetta_bench.sandbox import DockerSandbox, parse_unittest_output

LIVE = pytest.mark.skipif(os.environ.get("ROSETTA_BENCH_DOCKER") != "1", reason="set ROSETTA_BENCH_DOCKER=1 to run real containers")


class FakeRunner:
    def __init__(self, returncode=0, stdout="", stderr="Ran 2 tests in 0.001s\n\nOK\n", raise_timeout=False):
        self.calls = []
        self.result = subprocess.CompletedProcess([], returncode, stdout, stderr)
        self.raise_timeout = raise_timeout

    def __call__(self, cmd, **kwargs):
        self.calls.append((cmd, kwargs))
        if self.raise_timeout and cmd[1] == "run":
            raise subprocess.TimeoutExpired(cmd, kwargs.get("timeout"))
        return self.result


def test_container_is_isolated_and_limited():
    runner = FakeRunner()
    DockerSandbox(runner=runner).run_tests({"solution.py": "x = 1\n", "test_task.py": "import unittest\n"})
    cmd, kwargs = runner.calls[0]
    docker_options = cmd[:cmd.index("python:3.12-slim")]
    for flag in ("--network", "none", "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                 "--pids-limit", "--memory", "--cpus", "--user", "65534:65534", "--rm"):
        assert flag in docker_options, flag
    mounts = [docker_options[i + 1] for i, part in enumerate(docker_options) if part == "-v"]
    assert len(mounts) == 1 and mounts[0].endswith(":/work:ro")
    assert "-e" not in cmd[:cmd.index("python:3.12-slim")] or all(
        not cmd[i + 1].startswith(("JEVMODEL", "OLLAMA", "ANTHROPIC")) for i, p in enumerate(cmd) if p == "-e"
    )
    assert kwargs["timeout"] > 0


def test_workspace_is_outside_any_source_checkout_and_removed_afterwards():
    runner = FakeRunner()
    sandbox = DockerSandbox(runner=runner)
    sandbox.run_tests({"solution.py": "x = 1\n", "test_task.py": "import unittest\n"})
    cmd, _ = runner.calls[0]
    docker_options = cmd[:cmd.index("python:3.12-slim")]
    host_dir = [docker_options[i + 1] for i, part in enumerate(docker_options) if part == "-v"][0].rsplit(":/work", 1)[0]
    assert ".worktrees" not in host_dir and "rosetta" not in host_dir.lower().replace("rosetta-sandbox", "")
    assert not os.path.exists(host_dir)


def test_file_names_are_restricted_to_the_workspace():
    with pytest.raises(ValueError):
        DockerSandbox(runner=FakeRunner()).run_tests({"../escape.py": "x"})


def test_passing_run_is_reported():
    result = DockerSandbox(runner=FakeRunner(stderr="test_a ... ok\n\nRan 3 tests in 0.002s\n\nOK\n")).run_tests({"test_task.py": ""})
    assert (result.passed, result.tests_run, result.failures, result.timed_out) == (True, 3, 0, False)


def test_failures_and_errors_are_counted():
    stderr = "Ran 4 tests in 0.01s\n\nFAILED (failures=1, errors=2)\n"
    result = DockerSandbox(runner=FakeRunner(returncode=1, stderr=stderr)).run_tests({"test_task.py": ""})
    assert (result.passed, result.tests_run, result.failures) == (False, 4, 3)


def test_a_timeout_kills_the_container_and_fails():
    runner = FakeRunner(raise_timeout=True)
    result = DockerSandbox(runner=runner, timeout_s=5).run_tests({"test_task.py": ""})
    assert result.timed_out and result.passed is False
    assert any(call[0][1] == "kill" for call in runner.calls)


def test_no_tests_run_is_not_a_pass():
    assert parse_unittest_output("Ran 0 tests in 0.000s\n\nNO TESTS RAN\n", 5)[0] is False


@LIVE
def test_live_correct_code_passes():
    files = {
        "solution.py": "def add(a, b):\n    return a + b\n",
        "test_task.py": "import unittest\nfrom solution import add\n\nclass T(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(add(2, 3), 5)\n",
    }
    result = DockerSandbox().run_tests(files)
    assert result.passed, result.stderr_tail


@LIVE
def test_live_container_has_no_network_no_credentials_and_a_read_only_workspace(monkeypatch):
    monkeypatch.setenv("JEVMODEL_API_KEY", "must-not-leak")
    probe = (
        "import os, socket, unittest\n\n"
        "class Isolation(unittest.TestCase):\n"
        "    def test_no_network(self):\n"
        "        with self.assertRaises(OSError):\n"
        "            socket.create_connection(('1.1.1.1', 53), timeout=3)\n"
        "    def test_no_credentials(self):\n"
        "        self.assertNotIn('JEVMODEL_API_KEY', os.environ)\n"
        "    def test_workspace_read_only(self):\n"
        "        with self.assertRaises(OSError):\n"
        "            open('/work/escape.txt', 'w')\n"
        "    def test_not_root(self):\n"
        "        self.assertNotEqual(os.getuid(), 0)\n"
    )
    result = DockerSandbox().run_tests({"test_isolation.py": probe})
    assert result.passed and result.tests_run == 4, result.stderr_tail


@LIVE
def test_live_infinite_loop_times_out():
    files = {"test_task.py": "import unittest\n\nclass T(unittest.TestCase):\n    def test_loop(self):\n        while True:\n            pass\n"}
    result = DockerSandbox(timeout_s=5).run_tests(files)
    assert result.timed_out and not result.passed
