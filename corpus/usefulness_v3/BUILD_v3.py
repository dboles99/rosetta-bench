"""Build corpus/usefulness_v3 = usefulness_v2 + a REPORT_DEFECT rule in every route contract (via rosetta-core
sync, P/H/M kept equivalent) + defect tasks. Usage: python build_usefulness_v3.py <bench_worktree>"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

bench = Path(sys.argv[1])
v2, v3 = bench / "corpus" / "usefulness_v2", bench / "corpus" / "usefulness_v3"
shutil.copytree(v2, v3)
cli = [sys.executable, "-m", "rosetta_core.cli"]
FIELD = "IF_DEFECT=reply REPORT_DEFECT: <the defect and where it is>"
NOTE = ("- If the request's own specification, examples or tests contain a mistake, reply with no code and a single\n"
        "  line REPORT_DEFECT: followed by the defect and where it is, instead of working around it.")
NOTES_END = "<!-- /ROSETTA:NOTES -->"


def sync(route: str, folder: Path) -> str:
    return subprocess.run(cli + ["sync", route, "--dir", str(folder)], capture_output=True, text=True, check=True).stdout.strip()


for folder in sorted(p for p in (v3 / "routes").iterdir() if p.is_dir()):
    route = folder.name
    schema_path = folder / f"{route}.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    schema["required"] = sorted(set(schema["required"]) - {"SCHEMA_VER"} | {"IF_DEFECT"}) + ["SCHEMA_VER"]
    schema["properties"]["IF_DEFECT"] = {"type": "string"}
    schema_path.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8", newline="\n")

    cpn = folder / f"{route}.cpn"
    lines = cpn.read_text(encoding="utf-8").splitlines()
    packet = [lines[0]] + sorted(lines[1:] + [FIELD])
    cpn.write_text("\n".join(packet) + "\n", encoding="utf-8", newline="\n")
    assert sync(route, folder) == "sync: machine-to-human", route

    md = folder / f"{route}.md"
    text = md.read_text(encoding="utf-8")
    assert NOTES_END in text, route
    md.write_text(text.replace(NOTES_END, NOTE + "\n" + NOTES_END, 1), encoding="utf-8", newline="\n")
    before = cpn.read_text(encoding="utf-8")
    assert sync(route, folder) == "sync: human-to-machine", route
    assert cpn.read_text(encoding="utf-8") == before, f"{route}: packet changed on a notes-only edit"
    assert sync(route, folder) == "sync: no-op", route
    result = subprocess.run(cli + ["validate", route, "--dir", str(folder)], capture_output=True, text=True)
    assert result.stdout.strip() == "valid", (route, result.stdout, result.stderr)

DEFECT_TASKS = [
    {"task_id": "r01", "language": "en", "request_text":
        "Implement `celsius_to_fahrenheit(c)` using the formula F = C * 9/5 + 32. It must pass these tests:\n\n"
        "    assert celsius_to_fahrenheit(0) == 32\n    assert celsius_to_fahrenheit(100) == 212\n"
        "    assert celsius_to_fahrenheit(-40) == -32",
     "check": {"mentions": [["-40"]]}},
    {"task_id": "r02", "language": "zh", "request_text":
        "实现 `is_leap(year)`：能被 4 整除且不能被 100 整除，或者能被 400 整除的年份是闰年。\n"
        "示例：is_leap(2024) 返回 True；is_leap(1900) 返回 False；is_leap(2000) 返回 False。",
     "check": {"mentions": [["2000"]]}},
    {"task_id": "r03", "language": "ja", "request_text":
        "関数 `word_count(text)` を実装してください。空白で区切った単語の数を返します（連続する空白は一つの区切りとみなします）。\n"
        "テスト:\n    assert word_count('a b c') == 3\n    assert word_count('') == 0\n    assert word_count('hello  world') == 3",
     "check": {"mentions": [["hello"]]}},
    {"task_id": "r04", "language": "en", "request_text":
        "Write `seconds_in(days)` that returns days multiplied by 86,400 seconds per day. Tests:\n\n"
        "    assert seconds_in(1) == 86400\n    assert seconds_in(2) == 172800\n    assert seconds_in(3) == 258200",
     "check": {"mentions": [["259200", "259,200", "258200", "258,200"]]}},
]
existing = {json.loads(l)["task_id"] for l in (v3 / "tasks.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
clash = existing & {t["task_id"] for t in DEFECT_TASKS}
assert not clash, f"task id collision with v2: {sorted(clash)}"
with (v3 / "tasks.jsonl").open("a", encoding="utf-8", newline="\n") as handle:
    for task in DEFECT_TASKS:
        handle.write(json.dumps({"task_id": task["task_id"], "kind": "defect", "language": task["language"], "entry_point": None,
                                 "request_text": task["request_text"], "expected_route": "code_change", "tags": ["defect"],
                                 "check": task["check"]}, ensure_ascii=False) + "\n")
readme = v3 / "README.md"
readme.write_text(readme.read_text(encoding="utf-8").rstrip("\n") + "\n\n## v3 additions\n\n"
                  "usefulness_v3 = usefulness_v2 + a REPORT_DEFECT rule in every route contract (IF_DEFECT field and a\n"
                  "matching notes sentence, applied with `rosetta sync` so P, H and M stay equivalent) + 4 `defect` tasks\n"
                  "(r01-r04, en/zh/ja) whose own tests or examples contradict their stated rule. Success: REPORT_DEFECT naming\n"
                  "the defect, with no code; code that works around the defect is scored `complied`. v2 tasks are unchanged.\n",
                  encoding="utf-8", newline="\n")
print(f"built {v3}: {sum(1 for _ in (v3 / 'routes').iterdir())} contracts updated, {len(DEFECT_TASKS)} defect tasks added")
