from dataclasses import dataclass

from rosetta_bench.corpus import Case
from rosetta_bench.judge import JudgeCallFn, score_trial
from rosetta_bench.models import RunResult, Task, Trial
from rosetta_bench.pricing import estimate_cost
from rosetta_bench.runners.base import Runner
from rosetta_bench.scoring.comprehension import ComprehensionScore, build_comprehension_prompt, score_comprehension
from rosetta_bench.timing import StageTimer


@dataclass(frozen=True)
class ComprehensionOutcome:
    score: ComprehensionScore
    run_result: RunResult
    prompt_chars: int


def run_comprehension(runner: Runner, case: Case, prompt_format: str, timer: StageTimer | None = None) -> ComprehensionOutcome:
    """Suite A as designed: the answer-key questions are appended to the document and
    the reply is scored against the key. (`run_trial` keeps its v1 behaviour.)"""
    timer = timer or StageTimer()
    document = case.human_text if prompt_format == "HUMAN" else case.machine_text
    prompt = build_comprehension_prompt(document, case.answer_key)
    with timer.stage("generation"):
        result = runner.run(prompt, None)
    with timer.stage("scoring"):
        score = score_comprehension(result.raw_output, case.answer_key)
    return ComprehensionOutcome(score=score, run_result=result, prompt_chars=len(prompt))


def run_trial(
    runner: Runner,
    case: Case,
    prompt_format: str,
    suite: str,
    judge_call_fn: JudgeCallFn | None,
    trial_id: str,
    timestamp: str,
) -> Trial:
    prompt_text = case.human_text if prompt_format == "HUMAN" else case.machine_text

    task: Task | None = None
    if suite == "TASK_COMPLETION":
        task = Task(
            name=case.task_spec["name"],
            instructions=case.task_spec["instructions"],
            reference_output=case.task_spec.get("reference_output"),
        )

    result = runner.run(prompt_text, task)

    quality_score = None
    judge_justification = ""
    if suite == "TASK_COMPLETION" and judge_call_fn is not None:
        judge_result = score_trial(
            task.instructions, result.raw_output, task.reference_output, judge_call_fn
        )
        quality_score = judge_result.mean_score
        judge_justification = judge_result.justification

    cost_usd = estimate_cost(runner.name, runner.model, result.tokens_in, result.tokens_out)

    return Trial(
        trial_id=trial_id,
        timestamp=timestamp,
        tool=runner.name,
        model=runner.model,
        prompt_id=case.case_id,
        prompt_format=prompt_format,
        suite=suite,
        tokens_in=result.tokens_in,
        tokens_out=result.tokens_out,
        latency_ms=result.latency_ms,
        turns=result.turns,
        task_success=None,
        comprehension_accuracy=None,  # answer-key scoring is a documented follow-up, not built here
        quality_score=quality_score,
        judge_justification=judge_justification,
        cost_usd=cost_usd,
        raw_output=result.raw_output,
    )
