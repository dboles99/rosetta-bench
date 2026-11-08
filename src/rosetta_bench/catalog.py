"""Experiment record-keeping: run log (JSON Lines + Markdown) and a SQLite database.

The run folders under results/runs are the source of truth. runs.jsonl and
EXPERIMENT_LOG.md are append-only logs; the database is rebuilt from the folders on
demand, so it can always be regenerated and never drifts from the evidence."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from rosetta_bench.usefulness.report import arm_metrics


def _lines(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()] if path.exists() else []


def _manifest_path(run_dir: Path) -> Path:
    for name in ("manifest.json", "probe.json"):
        if (run_dir / name).exists():
            return run_dir / name
    raise FileNotFoundError(f"{run_dir} has no manifest.json or probe.json")


def run_kind(run_dir: Path) -> str:
    path = _manifest_path(Path(run_dir))
    if path.name == "probe.json":
        return "probe"
    schema = json.loads(path.read_text(encoding="utf-8")).get("schema", "")
    if "decision-run" in schema:
        return "decision"
    if "usefulness" in schema:
        return "usefulness"
    if "run-manifest" in schema:
        return "experiment"
    return "unknown"


def summarize_run(run_dir: Path) -> dict:
    run_dir = Path(run_dir)
    kind = run_kind(run_dir)
    meta = json.loads(_manifest_path(run_dir).read_text(encoding="utf-8"))
    summary: dict = {"kind": kind, "run_id": meta.get("run_id", run_dir.name), "created_at": meta.get("created_at"),
                     "synthetic": meta.get("synthetic", False), "live": meta.get("live", kind == "probe")}
    if kind == "decision":
        rows = _lines(run_dir / "decisions.jsonl")
        called = [d for d in rows if d["answers"]]
        top1 = [d for d in called if d["label_fits"] and d["label_route"] in d["eligible_routes"]]
        summary.update({
            "provider": meta["provider"]["profile"], "model": meta["provider"]["requested_model"],
            "question_set": meta["question_set"]["version"], "split": meta.get("split"), "cases": len(rows),
            "top1": f"{sum(d['answers']['workflow_route']['selected'] == d['label_route'] for d in top1)}/{len(top1)}",
            "false_accepts": sum(1 for d in rows if not d["label_fits"] and d["outcome"] == "ACCEPT"),
            "input_tokens": sum(d["input_tokens"] or 0 for d in called),
        })
    elif kind == "usefulness":
        trials = _lines(run_dir / "trials.jsonl")
        arms: dict[str, list] = {}
        for t in trials:
            arms.setdefault(t["arm"], []).append(t)
        summary.update({
            "generator": meta["generator"]["model"], "providers": sorted(meta.get("providers", {})),
            "trials": len(trials), "stopped_early": meta.get("stopped_early"),
            "arms": {arm: {k: arm_metrics(rows)[k] for k in ("successes", "n", "accuracy", "tokens_per_success", "p50_ms")}
                     for arm, rows in sorted(arms.items())},
        })
    elif kind == "probe":
        summary.update({"provider": meta["profile"], "served_model": meta["served_model"], "http_status": meta["http_status"],
                        "input_tokens": meta["input_tokens"], "error": meta["error"]})
    elif kind == "experiment":
        summary.update({"trials": len(_lines(run_dir / "trials.jsonl")), "arms": [a["id"] for a in meta["arms"]]})
    return summary


def _one_line(summary: dict) -> str:
    kind = summary["kind"]
    if kind == "decision":
        return (f"{summary['provider']} `{summary['model']}`, question set {summary['question_set']}, {summary['cases']} cases"
                f"{', split ' + summary['split'] if summary.get('split') else ''}: top-1 {summary['top1']}, "
                f"false accepts {summary['false_accepts']}, {summary['input_tokens']:,} decision tokens")
    if kind == "usefulness":
        best = max(summary["arms"].items(), key=lambda kv: (kv[1]["accuracy"] or 0), default=(None, None))
        return (f"generator `{summary['generator']}`, providers {summary['providers'] or 'none'}, {summary['trials']} trials, "
                f"{len(summary['arms'])} arms; highest accuracy {best[0]} {best[1]['successes']}/{best[1]['n']}"
                + (f"; stopped early: {summary['stopped_early']}" if summary.get("stopped_early") else ""))
    if kind == "probe":
        return f"{summary['provider']} probe: HTTP {summary['http_status']}, served {summary['served_model']}, {summary['input_tokens']} tokens"
    return f"{summary.get('trials', '?')} trials"


def log_run(results_dir: Path, run_dir: Path, note: str = "") -> dict:
    results_dir, run_dir = Path(results_dir), Path(run_dir)
    log_path = results_dir / "runs.jsonl"
    relative = run_dir.resolve().relative_to(results_dir.resolve()).as_posix() if run_dir.resolve().is_relative_to(results_dir.resolve()) else str(run_dir)
    if any(entry["path"] == relative for entry in _lines(log_path)):
        raise ValueError(f"{relative} is already in the log")
    summary = summarize_run(run_dir)
    entry = {
        "logged_at": datetime.now(timezone.utc).isoformat(), "path": relative, "note": note,
        "manifest_sha256": hashlib.sha256(_manifest_path(run_dir).read_bytes()).hexdigest(), **summary,
    }
    results_dir.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    markdown = results_dir / "EXPERIMENT_LOG.md"
    if not markdown.exists():
        markdown.write_text("# Experiment log\n\nOne entry per run, newest last. Generated by `bench results log`; "
                            "the run folders are the evidence.\n", encoding="utf-8", newline="\n")
    flags = ("SYNTHETIC" if summary["synthetic"] else "real") + (", live" if summary["live"] else ", offline")
    with markdown.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(f"\n## {entry['logged_at'][:16].replace('T', ' ')} UTC · {summary['kind']} · `{relative}`\n\n"
                     f"- Run `{summary['run_id']}` ({flags})\n- {_one_line(summary)}\n" + (f"- Note: {note}\n" if note else ""))
    return entry


SCHEMA = """
CREATE TABLE runs (run_id TEXT, path TEXT PRIMARY KEY, kind TEXT, created_at TEXT, synthetic INTEGER, live INTEGER,
                   summary_json TEXT, manifest_json TEXT);
CREATE TABLE corpora (corpus TEXT PRIMARY KEY, digest TEXT, items INTEGER);
CREATE TABLE decision_cases (run_path TEXT, provider TEXT, model TEXT, question_set TEXT, case_id TEXT, category TEXT,
                   language TEXT, label_fits INTEGER, label_route TEXT, outcome TEXT, route TEXT, selected TEXT,
                   p_fit REAL, p_selected REAL, served_model TEXT, input_tokens INTEGER, decision_ms REAL);
CREATE TABLE usefulness_decisions (run_path TEXT, provider TEXT, task_id TEXT, kind TEXT, language TEXT, outcome TEXT,
                   route TEXT, p_fit REAL, p_selected REAL, served_model TEXT, input_tokens INTEGER, decision_ms REAL);
CREATE TABLE usefulness_trials (run_path TEXT, arm TEXT, rep TEXT, decider TEXT, task_id TEXT, kind TEXT, language TEXT,
                   route TEXT, decision_outcome TEXT, declined_by TEXT, generated INTEGER, cache_hit INTEGER,
                   generator_tokens_in INTEGER, generator_tokens_out INTEGER, decision_tokens INTEGER, success INTEGER,
                   sandbox_passed INTEGER, tests_run INTEGER, total_ms REAL, decision_ms REAL, generation_ms REAL,
                   sandbox_ms REAL, postflight_p REAL, error TEXT);
CREATE TABLE receipts (run_path TEXT, receipt_id TEXT, case_id TEXT, mode TEXT, provider TEXT, served_model TEXT,
                   outcome TEXT, executed_route TEXT, verified_success INTEGER, cost_basis TEXT, receipt_json TEXT);
CREATE TABLE probes (run_path TEXT, provider TEXT, requested_model TEXT, served_model TEXT, http_status INTEGER,
                   input_tokens INTEGER, tokens_remaining TEXT, elapsed_ms REAL, fields_json TEXT, error_json TEXT);
"""


def _b(value):
    return None if value is None else int(bool(value))


def build_db(results_dir: Path, db_path: Path) -> dict:
    results_dir, db_path = Path(results_dir), Path(db_path)
    if db_path.exists():
        db_path.unlink()
    run_dirs = sorted(p for p in (results_dir / "runs").iterdir() if p.is_dir()) if (results_dir / "runs").exists() else []
    con = sqlite3.connect(db_path)
    try:
        con.executescript(SCHEMA)
        corpora: dict[str, tuple] = {}
        for run_dir in run_dirs:
            try:
                kind = run_kind(run_dir)
            except FileNotFoundError:
                continue
            path = run_dir.relative_to(results_dir).as_posix()
            meta = json.loads(_manifest_path(run_dir).read_text(encoding="utf-8"))
            summary = summarize_run(run_dir)
            con.execute("INSERT INTO runs VALUES (?,?,?,?,?,?,?,?)", (summary["run_id"], path, kind, summary["created_at"],
                        _b(summary["synthetic"]), _b(summary["live"]), json.dumps(summary), json.dumps(meta)))
            if kind == "decision":
                corpora[Path(meta["corpus_dir"]).name] = (meta["corpus_digest"], len(_lines(run_dir / "decisions.jsonl")))
                for d in _lines(run_dir / "decisions.jsonl"):
                    s = d["signals"]
                    selected = (d["answers"] or {}).get("workflow_route", {}).get("selected")
                    con.execute("INSERT INTO decision_cases VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                        path, meta["provider"]["profile"], meta["provider"]["requested_model"], meta["question_set"]["version"],
                        d["case_id"], d["category"], d["language"], _b(d["label_fits"]), d["label_route"], d["outcome"],
                        d["route"], selected, s.get("route_fits.p_yes"), s.get("workflow_route.p_selected"),
                        d["served_model"], d["input_tokens"], d["decision_ms"]))
            elif kind == "usefulness":
                corpora[Path(meta["corpus_dir"]).name] = (meta["corpus_digest"], None)
                for d in _lines(run_dir / "decisions.jsonl"):
                    s = d["signals"]
                    con.execute("INSERT INTO usefulness_decisions VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (
                        path, d["provider"], d["task_id"], d["kind"], d["language"], d["outcome"], d["route"],
                        s.get("route_fits.p_yes"), s.get("workflow_route.p_selected"), d["served_model"], d["input_tokens"], d["decision_ms"]))
                for t in _lines(run_dir / "trials.jsonl"):
                    tm = t["timings_ms"]
                    con.execute("INSERT INTO usefulness_trials VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                        path, t["arm"], t["rep"], t["decider"], t["task_id"], t["kind"], t["language"], t["route"],
                        (t["decision"] or {}).get("outcome"), t["declined_by"], _b(t["generated"]), _b(t["generation_cache_hit"]),
                        t["generator_tokens_in"], t["generator_tokens_out"], t["decision_tokens"], _b(t["success"]),
                        _b(t["sandbox"]["passed"]) if t["sandbox"] else None, t["sandbox"]["tests_run"] if t["sandbox"] else None,
                        tm.get("total"), tm.get("decision"), tm.get("generation"), tm.get("sandbox"),
                        (t["postflight"] or {}).get("addresses_task"), t["error"]))
            elif kind == "probe":
                con.execute("INSERT INTO probes VALUES (?,?,?,?,?,?,?,?,?,?)", (
                    path, meta["profile"], meta["requested_model"], meta["served_model"], meta["http_status"], meta["input_tokens"],
                    meta["tokens_remaining"], meta["elapsed_ms"], json.dumps(meta["fields"]), json.dumps(meta["error"])))
            for r in _lines(run_dir / "receipts.jsonl"):
                con.execute("INSERT INTO receipts VALUES (?,?,?,?,?,?,?,?,?,?,?)", (
                    path, r["receipt_id"], r["case_id"], r["mode"], (r["provider"] or {}).get("name"),
                    (r["provider"] or {}).get("served_model"), (r["recommendation"] or {}).get("outcome"), r["executed_route"],
                    _b(r["outcome"]["verified_success"]), r["cost"]["basis"], json.dumps(r)))
        for corpus, (digest, items) in corpora.items():
            con.execute("INSERT OR REPLACE INTO corpora VALUES (?,?,?)", (corpus, digest, items))
        con.commit()
        tables = ("runs", "corpora", "decision_cases", "usefulness_decisions", "usefulness_trials", "receipts", "probes")
        return {table: con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in tables}
    finally:
        con.close()
