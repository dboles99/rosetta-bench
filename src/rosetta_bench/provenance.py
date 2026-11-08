import subprocess
from pathlib import Path


def git_state(path: Path) -> dict | None:
    """Commit SHA and dirty flag of the git checkout containing `path`, or None."""
    try:
        sha = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True, timeout=10,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "-C", str(path), "status", "--porcelain"],
            capture_output=True, text=True, check=True, timeout=10,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    return {"sha": sha, "dirty": bool(status.strip())}
