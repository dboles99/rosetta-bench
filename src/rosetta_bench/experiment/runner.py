"""Offline paired runner: every arm sees the same cases and suites in a seeded random
order; the manifest records that order, the case digests and the repo state."""
import hashlib
import json
import platform
import random
import sys
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import rosetta_bench
from rosetta_bench.corpus import Case, load_case
from rosetta_bench.experiment.config import ArmConfig, ExperimentConfig
from rosetta_bench.experiment.fakes import FakeGenerator
from rosetta_bench.harness import run_comprehension
from rosetta_bench.models import Task
from rosetta_bench.pricing import estimate_cost_v2
from rosetta_bench.provenance import git_state
from rosetta_bench.results_v2 import MANIFEST_SCHEMA, TRIAL_SCHEMA, RunWriter
from rosetta_bench.scoring.constraints import check_constraints, task_success
from rosetta_bench.timing import StageTimer

BENCH_ROOT = Path(rosetta_bench.__file__).resolve().parents[2]


def case_digest(case: Case) -> str:
    payload = json.dumps(
        {"human": case.human_text, "machine": case.machine_text, "answer_key": case.answer_key, "task_spec": case.task_spec},
        sort_keys=True, ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def plan_trials(config: ExperimentConfig) -> list[tuple[str, ArmConfig, str, str, int]]:
    planned = [
        (f"{arm.arm_id}|{case_id}|{suite}|r{repeat}", arm, case_id, suite, repeat)
        for case_id in config.cases
        for arm in config.arms
        for suite in config.suites
        for repeat in range(config.repeats)
    ]
    random.Random(config.seed).shuffle(planned)
    return [(f"t{index:04d}:{key}", arm, case_id, suite, repeat) for index, (key, arm, case_id, suite, repeat) in enumerate(planned)]


def _generator(arm: ArmConfig):
    if arm.generator_kind == "fake":
        return FakeGenerator(arm.generator_model)
    raise ValueError(f"no generator for kind {arm.generator_kind!r}")


def _run_one(trial_id, order_index, arm, case, suite, repeat, run_id, synthetic) -> dict:
    runner = _generator(arm)
    timer = StageTimer()
    record = {
        "schema": TRIAL_SCHEMA, "run_id": run_id, "trial_id": trial_id, "order_index": order_index,
        "arm": arm.arm_id, "case_id": case.case_id, "suite": suite, "prompt_format": arm.prompt_format,
        "repeat": repeat, "tool": runner.name, "model": runner.model, "synthetic": synthetic,
        "tokens_in": None, "tokens_out": None, "comprehension_accuracy": None, "comprehension_items": None,
        "constraint_results": None, "task_success": None, "quality_score": None, "error": None, "raw_output": None,
    }
    try:
        if suite == "COMPREHENSION":
            outcome = run_comprehension(runner, case, arm.prompt_format, timer)
            result = outcome.run_result
            record["comprehension_accuracy"] = outcome.score.accuracy
            record["comprehension_items"] = [asdict(item) for item in outcome.score.items]
        else:
            spec = case.task_spec
            task = Task(name=spec["name"], instructions=spec["instructions"], reference_output=spec.get("reference_output"))
            document = case.human_text if arm.prompt_format == "HUMAN" else case.machine_text
            with timer.stage("generation"):
                result = runner.run(document, task)
            with timer.stage("scoring"):
                checks = check_constraints(result.raw_output, spec.get("constraints", []))
            record["constraint_results"] = [asdict(check) for check in checks]
            record["task_success"] = task_success(checks)
        record.update(tokens_in=result.tokens_in, tokens_out=result.tokens_out, raw_output=result.raw_output)
    except Exception as exc:  # a failed call is a recorded failure, never a silent skip
        record["error"] = f"{type(exc).__name__}: {exc}"
        if suite == "TASK_COMPLETION":
            record["task_success"] = False
    record["timings_ms"] = timer.timings_ms
    record["cost"] = estimate_cost_v2(runner.name, runner.model, record["tokens_in"], record["tokens_out"]).to_dict()
    return record


def run_experiment(config: ExperimentConfig, out_dir: Path) -> Path:
    config.require_offline()
    writer = RunWriter(out_dir)
    cases = {case_id: load_case(config.corpus_dir, case_id) for case_id in config.cases}
    trials = plan_trials(config)
    run_id = f"run-{uuid.uuid4().hex[:12]}"
    writer.write_manifest({
        "schema": MANIFEST_SCHEMA,
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "experiment": config.experiment,
        "synthetic": config.synthetic,
        "seed": config.seed,
        "arms": [arm.to_dict() for arm in config.arms],
        "case_ids": list(config.cases),
        "case_digests": {case_id: case_digest(case) for case_id, case in cases.items()},
        "suites": list(config.suites),
        "repeats": config.repeats,
        "trial_order": [trial[0] for trial in trials],
        "repos": {"bench": git_state(BENCH_ROOT), "core": None},
        "environment": {"python": sys.version.split()[0], "platform": platform.platform()},
        "notes": "Repeats are not independent cases; the case is the unit of paired resampling.",
    })
    for index, (trial_id, arm, case_id, suite, repeat) in enumerate(trials):
        writer.append_trial(_run_one(trial_id, index, arm, cases[case_id], suite, repeat, run_id, config.synthetic))
    return Path(out_dir)
