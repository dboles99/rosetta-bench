from pathlib import Path
from rosetta_bench.corpus import load_case


def _write_case(corpus_dir: Path, case_id: str):
    case_dir = corpus_dir / case_id
    case_dir.mkdir(parents=True)
    (case_dir / "human.md").write_text("# Human doc\ncontent", encoding="utf-8")
    (case_dir / "machine.cpn").write_text("SCHEMA_VER=1.0\nTASK=X\n", encoding="utf-8")
    (case_dir / "answer_key.yaml").write_text(
        "- question: What is TASK?\n  answer: X\n", encoding="utf-8"
    )
    (case_dir / "task_spec.yaml").write_text(
        "name: validate\ninstructions: do the thing\nreference_output: null\n", encoding="utf-8"
    )


def test_load_case_reads_all_four_files(tmp_path: Path):
    _write_case(tmp_path, "example_case")
    case = load_case(tmp_path, "example_case")
    assert case.case_id == "example_case"
    assert "Human doc" in case.human_text
    assert "SCHEMA_VER=1.0" in case.machine_text
    assert case.answer_key == [{"question": "What is TASK?", "answer": "X"}]
    assert case.task_spec == {"name": "validate", "instructions": "do the thing", "reference_output": None}
