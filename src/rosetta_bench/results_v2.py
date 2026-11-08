"""Run-scoped results: manifest.json plus trials.jsonl per run directory.

The v1 `storage/trials.csv` format is untouched. Its rows are read through
`load_legacy_trials`, which labels their cost `legacy_unverified` rather than
reinterpreting historical zeros as free.
"""
import json
from pathlib import Path

from rosetta_bench.storage import load_trials

MANIFEST_SCHEMA = "rosetta-bench/run-manifest@1"
TRIAL_SCHEMA = "rosetta-bench/trial@2"
LEGACY_TRIAL_SCHEMA = "rosetta-bench/trial@legacy-csv"
REQUIRED_MANIFEST_KEYS = (
    "schema", "run_id", "created_at", "experiment", "synthetic", "seed",
    "arms", "case_ids", "trial_order", "repos", "environment",
)


class ManifestInvalid(ValueError):
    pass


class RunWriter:
    def __init__(self, run_dir: Path):
        self.run_dir = Path(run_dir)
        if (self.run_dir / "manifest.json").exists():
            raise FileExistsError(f"a run already exists in {self.run_dir}; choose a new --out directory")

    def write_manifest(self, manifest: dict) -> None:
        missing = [key for key in REQUIRED_MANIFEST_KEYS if key not in manifest]
        if missing:
            raise ManifestInvalid(f"manifest missing: {', '.join(missing)}")
        self.run_dir.mkdir(parents=True, exist_ok=True)
        text = json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        (self.run_dir / "manifest.json").write_text(text, encoding="utf-8", newline="\n")

    def append_trial(self, trial: dict) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        line = json.dumps(trial, ensure_ascii=False, allow_nan=False)
        with (self.run_dir / "trials.jsonl").open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(line + "\n")


def load_manifest(run_dir: Path) -> dict:
    return json.loads((Path(run_dir) / "manifest.json").read_text(encoding="utf-8"))


def load_trials_v2(run_dir: Path) -> list[dict]:
    path = Path(run_dir) / "trials.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_legacy_trials(csv_path: Path) -> list[dict]:
    rows = []
    for row in load_trials(csv_path):
        converted = dict(row)
        raw_cost = row.get("cost_usd")
        converted["schema"] = LEGACY_TRIAL_SCHEMA
        converted["cost"] = {
            "usd": float(raw_cost) if raw_cost else None,  # "" or missing -> unknown; "0.0" stays 0.0
            "basis": "legacy_unverified",
            "price_source": None,
            "price_as_of": None,
        }
        rows.append(converted)
    return rows
