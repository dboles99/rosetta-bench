import re
import subprocess
from pathlib import Path

import pytest

from rosetta_bench.provenance import git_state

REPO = Path(__file__).resolve().parent.parent


def _inside_git(path: Path) -> bool:
    try:
        subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"], check=True, capture_output=True)
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


def test_git_state_of_a_non_repository_is_none(tmp_path: Path):
    assert git_state(tmp_path) is None


@pytest.mark.skipif(not _inside_git(REPO), reason="source tree is not a git checkout")
def test_git_state_reports_the_commit_and_a_dirty_flag():
    state = git_state(REPO)
    assert re.fullmatch(r"[0-9a-f]{40}", state["sha"])
    assert isinstance(state["dirty"], bool)
