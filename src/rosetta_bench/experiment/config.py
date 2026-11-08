from dataclasses import dataclass
from pathlib import Path

import yaml

FORMATS = ("HUMAN", "MACHINE")
SUITES = ("COMPREHENSION", "TASK_COMPLETION")
OFFLINE_GENERATOR_KINDS = ("fake",)


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class ArmConfig:
    arm_id: str
    prompt_format: str
    generator_kind: str
    generator_model: str

    def to_dict(self) -> dict:
        return {
            "id": self.arm_id,
            "prompt_format": self.prompt_format,
            "generator": {"kind": self.generator_kind, "model": self.generator_model},
        }


@dataclass(frozen=True)
class ExperimentConfig:
    experiment: str
    seed: int
    corpus_dir: Path
    cases: tuple[str, ...]
    suites: tuple[str, ...]
    repeats: int
    arms: tuple[ArmConfig, ...]

    @property
    def synthetic(self) -> bool:
        return all(arm.generator_kind == "fake" for arm in self.arms)

    def require_offline(self) -> None:
        for arm in self.arms:
            if arm.generator_kind not in OFFLINE_GENERATOR_KINDS:
                raise ConfigError(
                    f"arm {arm.arm_id} uses live generator kind {arm.generator_kind!r}; "
                    "this build runs offline only (generator kind 'fake')"
                )


def _require(data: dict, key: str):
    if key not in data:
        raise ConfigError(f"config missing {key!r}")
    return data[key]


def load_config(path: Path) -> ExperimentConfig:
    path = Path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    seed = _require(data, "seed")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ConfigError("seed must be an integer")
    repeats = data.get("repeats", 1)
    if not isinstance(repeats, int) or repeats < 1:
        raise ConfigError("repeats must be a positive integer")
    suites = tuple(_require(data, "suites"))
    if not suites or any(suite not in SUITES for suite in suites):
        raise ConfigError(f"suites must be drawn from {SUITES}")
    cases = tuple(_require(data, "cases"))
    if not cases:
        raise ConfigError("at least one case is required")

    arms = []
    for raw in _require(data, "arms"):
        generator = raw.get("generator") or {}
        arm = ArmConfig(
            arm_id=str(raw.get("id", "")),
            prompt_format=raw.get("prompt_format", ""),
            generator_kind=generator.get("kind", ""),
            generator_model=generator.get("model", ""),
        )
        if not arm.arm_id or arm.prompt_format not in FORMATS or not arm.generator_kind or not arm.generator_model:
            raise ConfigError(f"arm {raw!r} needs id, prompt_format in {FORMATS}, generator.kind and generator.model")
        arms.append(arm)
    if not arms:
        raise ConfigError("at least one arm is required")
    if len({arm.arm_id for arm in arms}) != len(arms):
        raise ConfigError("arm ids must be unique")

    corpus_dir = Path(_require(data, "corpus_dir"))
    if not corpus_dir.is_absolute():
        corpus_dir = (path.parent / corpus_dir).resolve()

    return ExperimentConfig(
        experiment=str(_require(data, "experiment")),
        seed=seed,
        corpus_dir=corpus_dir,
        cases=cases,
        suites=suites,
        repeats=repeats,
        arms=tuple(arms),
    )
