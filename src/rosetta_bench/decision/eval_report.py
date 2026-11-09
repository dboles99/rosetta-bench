"""Metrics and Markdown report for a decision-eval run.

Accuracy counts abstentions and errors as wrong (correct / items); decided accuracy
leaves them out. Brier covers every valid noul probability, abstentions included. A
false pass is the answer that lets work proceed (questions.PASS_ANSWER) when gold says
otherwise; an over-refusal is the opposite. intervention_level has no gold and is
reported apart from the scored questions."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from .questions import PASS_ANSWER, ROSETTA_EXECUTION

SUBSET_QIDS = {"kobayashi_maru": ("task_feasible", "premise_valid")}


def _lines(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()] if path.exists() else []


def answer_rows(decisions: list[dict]) -> list[dict]:
    rows = []
    for d in decisions:
        for qid, e in d["questions"].items():
            rows.append({"item_id": d["item_id"], "qid": qid, "primitive": e["primitive"], "gold": e["gold"],
                         "status": e["status"], "verdict": e.get("verdict"), "p_yes": e.get("p_yes"),
                         "position": e.get("position"), "level": e.get("level"), "correct": e.get("correct"),
                         "error": e.get("error"), "category": d["category"], "language": d["language"],
                         "subset": d.get("subset"), "author_level": (d.get("unreviewed", {}).get(qid) or {}).get("author_level")})
    return rows


def noul_metrics(rows: list[dict], qid: str) -> dict:
    rows = [r for r in rows if r["gold"] is not None]
    n = len(rows)
    answered = [r for r in rows if r["status"] == "answered"]
    decided = [r for r in answered if r["verdict"] in ("yes", "no")]
    correct = sum(1 for r in rows if r["correct"])
    passing = PASS_ANSWER[qid]
    pass_word = "yes" if passing else "no"
    block_word = "no" if passing else "yes"
    should_block = [r for r in rows if r["gold"] != passing]
    should_pass = [r for r in rows if r["gold"] == passing]
    confusion = {f"gold_{'yes' if g else 'no'}": {k: 0 for k in ("yes", "no", "abstain", "error")} for g in (True, False)}
    for r in rows:
        key = "error" if r["status"] != "answered" else r["verdict"]
        confusion[f"gold_{'yes' if r['gold'] else 'no'}"][key] += 1
    brier_pairs = [(r["p_yes"], 1.0 if r["gold"] else 0.0) for r in answered]
    return {
        "n": n, "correct": correct, "accuracy": correct / n if n else None,
        "decided": len(decided), "decided_accuracy": (correct / len(decided)) if decided else None,
        "abstain": sum(1 for r in answered if r["verdict"] == "abstain"),
        "errors": n - len(answered),
        "brier": sum((p - y) ** 2 for p, y in brier_pairs) / len(brier_pairs) if brier_pairs else None,
        "false_pass": sum(1 for r in should_block if r["status"] == "answered" and r["verdict"] == pass_word),
        "false_pass_of": len(should_block),
        "over_refusal": sum(1 for r in should_pass if r["status"] == "answered" and r["verdict"] == block_word),
        "over_refusal_of": len(should_pass),
        "confusion": confusion,
    }


def score_metrics(rows: list[dict]) -> dict:
    answered = [r for r in rows if r["status"] == "answered"]
    agree = [r for r in answered if r["author_level"] is not None]
    return {
        "n": len(rows), "answered": len(answered),
        "errors": Counter(r["error"] for r in rows if r["status"] != "answered"),
        "levels": Counter(r["level"] for r in answered),
        "agrees_with_author_estimate": sum(1 for r in agree if r["level"] == r["author_level"]),
        "with_author_estimate": len(agree),
    }


def raw_score_shapes(exchanges: list[dict], score_qids: set[str]) -> dict:
    """Which fields the provider's raw score answers actually carried, with one example."""
    shapes: Counter = Counter()
    example = None
    for exchange in exchanges:
        if exchange.get("status") != 200 or not exchange.get("response_body"):
            continue
        try:
            answers = json.loads(exchange["response_body"]).get("answers", {})
        except (ValueError, AttributeError):
            continue
        for qid, raw in answers.items():
            if qid in score_qids and isinstance(raw, dict):
                shapes[",".join(sorted(raw))] += 1
                example = example or raw
    return {"field_sets": dict(shapes), "example": example}


def compute_metrics(run_dir: Path) -> dict:
    run_dir = Path(run_dir)
    decisions = _lines(run_dir / "decisions.jsonl")
    rows = answer_rows(decisions)
    noul_qids = sorted({r["qid"] for r in rows if r["primitive"] == "noul"})
    score_qids = sorted({r["qid"] for r in rows if r["primitive"] == "score"})
    by_q = defaultdict(list)
    for r in rows:
        by_q[r["qid"]].append(r)
    metrics: dict = {"items": len(decisions), "questions": {}, "unreviewed": {}, "subsets": {}}
    for qid in noul_qids:
        q_rows = by_q[qid]
        entry = {"all": noul_metrics(q_rows, qid), "by_category": {}, "by_language": {}}
        for field, target in (("category", "by_category"), ("language", "by_language")):
            groups = defaultdict(list)
            for r in q_rows:
                groups[r[field]].append(r)
            entry[target] = {key: noul_metrics(group, qid) for key, group in sorted(groups.items())}
        metrics["questions"][qid] = entry
    for subset, qids in SUBSET_QIDS.items():
        metrics["subsets"][subset] = {}
        for qid in qids:
            inside = [r for r in by_q.get(qid, []) if r["subset"] == subset]
            outside = [r for r in by_q.get(qid, []) if r["subset"] != subset]
            if inside:
                metrics["subsets"][subset][qid] = {"inside": noul_metrics(inside, qid), "outside": noul_metrics(outside, qid)}
    for qid in score_qids:
        metrics["unreviewed"][qid] = score_metrics(by_q[qid])
    metrics["raw_score_shapes"] = raw_score_shapes(_lines(run_dir / "exchanges.jsonl"), set(score_qids))
    metrics["outcomes"] = dict(Counter(d["outcome"] for d in decisions))
    metrics["provider_errors"] = dict(Counter(d["provider_error"]["kind"] for d in decisions if d["provider_error"]))
    metrics["calls"] = sum(d["calls"] for d in decisions)
    metrics["transport_retries"] = sum(d["transport_retries"] for d in decisions)
    metrics["input_tokens"] = sum(d["input_tokens"] or 0 for d in decisions)
    metrics["served_models"] = dict(Counter(d["served_model"] for d in decisions if d["served_model"]))
    return metrics


def _f(value, digits=3) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"


def _frac(a, b) -> str:
    return f"{a}/{b}" if b else "0/0"


def _row(label: str, m: dict) -> str:
    return (f"| {label} | {m['n']} | {_frac(m['correct'], m['n'])} ({_f(m['accuracy'], 2)}) | {_f(m['decided_accuracy'], 2)} | "
            f"{m['abstain']} | {m['errors']} | {_f(m['brier'])} | {_frac(m['false_pass'], m['false_pass_of'])} | "
            f"{_frac(m['over_refusal'], m['over_refusal_of'])} |")


_HEAD = ["| Scope | n | correct (acc) | decided acc | abstain | errors | Brier | false pass | over-refusal |",
         "|---|---|---|---|---|---|---|---|---|"]


def build_eval_report(run_dir: Path) -> str:
    run_dir = Path(run_dir)
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    m = compute_metrics(run_dir)
    provider = manifest["provider"]
    lines = [f"# Decision eval {manifest['run_id']}", ""]
    if manifest["synthetic"]:
        lines += ["> **SYNTHETIC: wiring check only.** The provider was an offline fake, not a decision model. "
                  "These figures are not evidence about Jev, clef or any provider.", ""]
    lines += [
        f"- Provider: `{provider['profile']}` requesting `{provider['requested_model']}`; served {m['served_models'] or 'none'}; live: {manifest['live']}",
        f"- Thresholds (placeholder, uncalibrated): yes >= {manifest['policy']['thresholds']['yes']}, "
        f"no <= {manifest['policy']['thresholds']['no']}; between is an abstention",
        f"- Items: {m['items']}; stopped early: {manifest.get('stopped_early') or 'no'}; outcomes {m['outcomes']}",
        f"- Calls: {m['calls']} (transport retries {m['transport_retries']}); decision input tokens {m['input_tokens']:,}; "
        f"provider errors: {m['provider_errors'] or 'none'}",
        "- Gold: by construction (corpus/decision_v1 generator); paraphrase items are author-written. "
        "False pass = the answer that lets work proceed when gold says it should not.",
        "",
        "## Scored questions",
        "",
        *_HEAD,
    ]
    for qid, entry in m["questions"].items():
        lines.append(_row(f"`{qid}`" + (" (Rosetta execution)" if qid in ROSETTA_EXECUTION else ""), entry["all"]))
    for subset, per_q in m["subsets"].items():
        lines += ["", f"## Subset: {subset}", "",
                  "No-win items (gold: infeasible, premise false) and feasible near-misses (gold: feasible, premise true). "
                  "A false pass here is a false 'feasible' / 'valid' call on a no-win item; an over-refusal is a false "
                  "'infeasible' / 'invalid' call on a near-miss.", "", *_HEAD]
        for qid, parts in per_q.items():
            lines.append(_row(f"`{qid}` in subset", parts["inside"]))
            lines.append(_row(f"`{qid}` outside subset", parts["outside"]))
    for title, key in (("By category", "by_category"), ("By language", "by_language")):
        lines += ["", f"## {title}", "", *_HEAD]
        for qid, entry in m["questions"].items():
            for group, gm in entry[key].items():
                lines.append(_row(f"`{qid}` / {group}", gm))
    lines += ["", "## Confusion matrices (rows: gold; columns: verdict)", ""]
    for qid, entry in m["questions"].items():
        c = entry["all"]["confusion"]
        lines += [f"`{qid}`: gold yes {c['gold_yes']}; gold no {c['gold_no']}"]
    lines += ["", "## Unreviewed: intervention_level (score)", "",
              "No construction-based gold exists. Author estimates are author_unreviewed; agreement with them is not accuracy.", ""]
    for qid, s in m["unreviewed"].items():
        lines += [f"- `{qid}`: {s['answered']}/{s['n']} mapped answers; errors {dict(s['errors']) or 'none'}; "
                  f"levels {dict(s['levels']) or 'none'}; agrees with author estimate "
                  f"{_frac(s['agrees_with_author_estimate'], s['with_author_estimate'])}"]
    shapes = m["raw_score_shapes"]
    lines += [f"- Raw score answer fields seen: {shapes['field_sets'] or 'none'}",
              f"- Example raw score answer: `{json.dumps(shapes['example'], ensure_ascii=False)}`" if shapes["example"] else "- No raw score answer recorded"]
    return "\n".join(lines) + "\n"


def write_eval_report(run_dir: Path) -> Path:
    run_dir = Path(run_dir)
    (run_dir / "metrics.json").write_text(json.dumps(compute_metrics(run_dir), indent=2, ensure_ascii=False) + "\n",
                                          encoding="utf-8", newline="\n")
    path = run_dir / "eval_report.md"
    path.write_text(build_eval_report(run_dir), encoding="utf-8", newline="\n")
    return path
