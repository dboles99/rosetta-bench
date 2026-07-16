from dataclasses import dataclass


@dataclass
class Task:
    name: str
    instructions: str
    reference_output: str | None = None


@dataclass
class RunResult:
    raw_output: str
    tokens_in: int
    tokens_out: int
    latency_ms: float
    turns: int = 1


@dataclass
class Trial:
    trial_id: str
    timestamp: str
    tool: str
    model: str
    prompt_id: str
    prompt_format: str
    suite: str
    tokens_in: int
    tokens_out: int
    latency_ms: float
    turns: int
    task_success: bool | None
    comprehension_accuracy: float | None
    quality_score: float | None
    judge_justification: str
    cost_usd: float
    raw_output: str

    def to_row(self) -> dict:
        return {
            "trial_id": self.trial_id,
            "timestamp": self.timestamp,
            "tool": self.tool,
            "model": self.model,
            "prompt_id": self.prompt_id,
            "prompt_format": self.prompt_format,
            "suite": self.suite,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "latency_ms": self.latency_ms,
            "turns": self.turns,
            "task_success": self.task_success,
            "comprehension_accuracy": self.comprehension_accuracy,
            "quality_score": self.quality_score,
            "judge_justification": self.judge_justification,
            "cost_usd": self.cost_usd,
            "raw_output": self.raw_output,
        }
