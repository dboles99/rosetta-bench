"""Run untrusted generated code against hidden acceptance tests inside a locked-down
Docker container: no network, read-only root and workspace, all capabilities dropped,
an unprivileged user, memory/CPU/process limits and a hard timeout. The workspace is a
fresh temporary directory (never a source checkout), deleted afterwards. The container
receives no host environment, so no credentials."""
from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

_SAFE_NAME = re.compile(r"^[A-Za-z0-9_]+\.py$")
_TAIL = 4000


@dataclass(frozen=True)
class SandboxResult:
    passed: bool
    tests_run: int
    failures: int
    timed_out: bool
    returncode: int | None
    stdout_tail: str
    stderr_tail: str
    elapsed_ms: float


def parse_unittest_output(text: str, returncode: int | None) -> tuple[bool, int, int]:
    ran = re.search(r"Ran (\d+) tests? in", text)
    tests_run = int(ran.group(1)) if ran else 0
    failed = re.search(r"FAILED \(([^)]*)\)", text)
    if failed:
        failures = sum(int(n) for n in re.findall(r"(?:failures|errors)=(\d+)", failed.group(1)))
        return False, tests_run, failures
    passed = returncode == 0 and tests_run > 0 and re.search(r"^OK\b", text, re.MULTILINE) is not None
    return passed, tests_run, 0


class DockerSandbox:
    def __init__(
        self,
        image: str = "python:3.12-slim",
        timeout_s: int = 60,
        memory: str = "256m",
        cpus: str = "1",
        pids: int = 64,
        docker: str = "docker",
        runner: Callable = subprocess.run,
    ):
        self.image = image
        self.timeout_s = timeout_s
        self.memory = memory
        self.cpus = cpus
        self.pids = pids
        self.docker = docker
        self._run = runner

    def command(self, host_dir: str, name: str) -> list[str]:
        return [
            self.docker, "run", "--rm", "--name", name,
            "--network", "none", "--read-only", "--tmpfs", "/tmp:rw,size=16m",
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "--pids-limit", str(self.pids), "--memory", self.memory, "--cpus", self.cpus,
            "--user", "65534:65534", "-e", "PYTHONDONTWRITEBYTECODE=1",
            "-v", f"{host_dir}:/work:ro", "-w", "/work",
            self.image,
            "timeout", "-s", "KILL", str(self.timeout_s),
            "python", "-B", "-m", "unittest", "discover", "-s", "/work", "-p", "test_*.py", "-v",
        ]

    def run_tests(self, files: dict[str, str]) -> SandboxResult:
        for name in files:
            if not _SAFE_NAME.match(name):
                raise ValueError(f"unsafe workspace file name: {name!r}")
        host_dir = tempfile.mkdtemp(prefix="rb-sandbox-")
        name = f"rb-sandbox-{uuid.uuid4().hex[:12]}"
        started = time.perf_counter()
        try:
            for file_name, content in files.items():
                (Path(host_dir) / file_name).write_text(content, encoding="utf-8", newline="\n")
            try:
                proc = self._run(self.command(host_dir, name), capture_output=True, text=True, timeout=self.timeout_s + 30)
            except subprocess.TimeoutExpired:
                self._run([self.docker, "kill", name], capture_output=True, text=True, timeout=30)
                return SandboxResult(False, 0, 0, True, None, "", "outer timeout: container killed", (time.perf_counter() - started) * 1000)
            output = (proc.stdout or "") + "\n" + (proc.stderr or "")
            passed, tests_run, failures = parse_unittest_output(output, proc.returncode)
            timed_out = proc.returncode in (124, 137) and tests_run == 0
            return SandboxResult(
                passed=passed and not timed_out, tests_run=tests_run, failures=failures, timed_out=timed_out,
                returncode=proc.returncode, stdout_tail=(proc.stdout or "")[-_TAIL:], stderr_tail=(proc.stderr or "")[-_TAIL:],
                elapsed_ms=(time.perf_counter() - started) * 1000,
            )
        finally:
            shutil.rmtree(host_dir, ignore_errors=True)
