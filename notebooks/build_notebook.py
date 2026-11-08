"""Create notebooks/decision_layer_analysis.ipynb and execute it so outputs are embedded.
Usage: python build_notebook.py <bench_worktree>"""
import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient

bench = Path(sys.argv[1])
nb_dir = bench / "notebooks"
nb_dir.mkdir(exist_ok=True)
md = nbformat.v4.new_markdown_cell
code = nbformat.v4.new_code_cell

cells = [
    md("""# Rosetta decision layer: analysis notebook

Reads `results/rosetta_bench.sqlite`, which `bench results db` rebuilds from the run folders in `results/runs/`
(the folders are the evidence; the database is derived). Re-run all cells after `bench results db` to refresh.

**What is compared**
- **Representation** of the generator's instructions: **P** plain prose prompt, **H** Rosetta human view (`.md`),
  **M** Rosetta machine view (`.cpn` packet).
- **Decision layer** before generation: **none**, **jevmodel** (Jev via jevmodel.org), **clef-ollama** (clef via Ollama),
  **consensus** (both must agree).
- **Outcome**: hidden acceptance tests in a Docker sandbox for code tasks; *no code produced* for no-code requests.

**Read the caveats before the numbers**: small task sets, author-written labels for the routing smoke corpus,
placeholder (uncalibrated) thresholds, one temperature-0 sample per prompt. Smoke runs establish wiring, not performance."""),
    code("""import json, sqlite3
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

DB = Path("..") / "results" / "rosetta_bench.sqlite"
con = sqlite3.connect(DB)
q = lambda sql, *args: pd.read_sql_query(sql, con, params=args)

# Chart palette: first three categorical slots (validated all-pairs, light mode) and chart ink.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]
SURFACE, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "axes.edgecolor": AXIS, "axes.labelcolor": INK2,
    "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK, "axes.titlecolor": INK, "axes.titlesize": 12,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "font.family": ["Segoe UI", "DejaVu Sans", "sans-serif"], "legend.frameon": False,
})
pd.set_option("display.width", 200)
print(f"database: {DB.resolve()}")"""),
    md("## 1. Runs and metadata\n\nEvery run, from the database's `runs` table, with the note from the experiment log."),
    code("""runs = q("SELECT path, kind, run_id, created_at, synthetic, live FROM runs ORDER BY path")
log = pd.read_json(Path("..") / "results" / "runs.jsonl", lines=True)[["path", "note"]]
runs.merge(log, on="path", how="left")"""),
    md("## 2. Representation × decision matrix\n\nThe latest **live** usefulness run. Each arm is charged the tokens and time of the generation, decision and sandbox calls it used."),
    code("""run = q("SELECT path FROM runs WHERE kind='usefulness' AND live=1 ORDER BY created_at DESC LIMIT 1").path[0]
trials = q("SELECT * FROM usefulness_trials WHERE run_path=?", run)
trials["tokens"] = trials.generator_tokens_in + trials.generator_tokens_out + trials.decision_tokens
REPS, DECIDERS = ["P", "H", "M"], ["none", "jevmodel", "clef-ollama", "consensus"]

def arm_table(t):
    g = t.groupby(["rep", "decider"])
    out = pd.DataFrame({
        "trials": g.size(),
        "verified successes": g.success.sum(),
        "accuracy": g.success.mean(),
        "generator tokens": g.apply(lambda x: (x.generator_tokens_in + x.generator_tokens_out).sum()),
        "decision tokens": g.decision_tokens.sum(),
        "p50 ms": g.total_ms.median(),
        "p95 ms": g.total_ms.quantile(0.95, interpolation="higher"),
    })
    out["tokens per verified success"] = (out["generator tokens"] + out["decision tokens"]) / out["verified successes"]
    return out

arms = arm_table(trials)
print(f"run: {run}  ·  trials: {len(trials)}  ·  every arm at 100%: {bool((arms.accuracy == 1).all())}")
arms.round(1)"""),
    code("""pd.concat({
    "accuracy": arms.accuracy.unstack()[DECIDERS].reindex(REPS),
    "tokens per verified success": arms["tokens per verified success"].unstack()[DECIDERS].reindex(REPS).round(0),
    "p50 ms": arms["p50 ms"].unstack()[DECIDERS].reindex(REPS).round(0),
}, axis=1)"""),
    md("### Tokens per verified success\n\nGenerator plus decision tokens divided by verified successes. Lower is cheaper. Values are labelled on the bars; the table above has the same figures."),
    code("""tps = arms["tokens per verified success"].unstack()[DECIDERS].reindex(REPS)
fig, ax = plt.subplots(figsize=(9, 4.2))
width, gap = 0.24, 0.02
for i, rep in enumerate(REPS):
    xs = [d + (i - 1) * (width + gap) for d in range(len(DECIDERS))]
    bars = ax.bar(xs, tps.loc[rep], width=width, color=SERIES[i], label=rep, zorder=3)
    ax.bar_label(bars, labels=[f"{v:,.0f}" for v in tps.loc[rep]], padding=2, fontsize=8, color=INK2)
ax.set_xticks(range(len(DECIDERS)), DECIDERS)
ax.set_ylabel("tokens per verified success")
ax.set_title("Tokens per verified success by decision layer and representation", loc="left")
ax.grid(axis="x", visible=False)
ax.legend(title="representation", ncols=3, loc="upper left")
plt.tight_layout(); plt.show()"""),
    md("### Where the time goes\n\nMean attributed milliseconds per stage, per arm, over **all** 18 trials: a stage a trial skipped (for example generation after a decline) counts as 0 ms, so every arm is averaged over the same trials. Decision time is the provider calls before generation; sandbox time is running the hidden tests."),
    code("""stage_cols = ["decision_ms", "generation_ms", "sandbox_ms"]
stages = trials.assign(**{c: trials[c].fillna(0) for c in stage_cols}).groupby("arm")[stage_cols].mean()
order = [f"{r}+{d}" for r in REPS for d in DECIDERS]
stages = stages.reindex(order)
fig, ax = plt.subplots(figsize=(9, 5))
left = [0.0] * len(stages)
for i, (col, label) in enumerate([("decision_ms", "decision"), ("generation_ms", "generation"), ("sandbox_ms", "sandbox")]):
    ax.barh(stages.index, stages[col], left=left, color=SERIES[i], label=label, height=0.62, edgecolor=SURFACE, linewidth=2, zorder=3)
    left = [l + v for l, v in zip(left, stages[col])]
for y, total in enumerate(left):
    ax.text(total + 80, y, f"{total:,.0f} ms", va="center", fontsize=8, color=INK2)
ax.invert_yaxis()
ax.set_xlabel("mean attributed ms per trial")
ax.set_title("Mean time per stage, by arm", loc="left")
ax.grid(axis="y", visible=False)
ax.set_xlim(0, max(left) * 1.12)
ax.legend(ncols=3, loc="upper left", bbox_to_anchor=(0, -0.12))
plt.tight_layout(); plt.show()"""),
    md("## 3. Paired contrasts\n\nPaired by task. *A better* / *B better* count tasks that one arm passed and the other failed. Ratios compare A with B (negative = A lower). Intervals are not estimated: 18 tasks is too few."),
    code("""def contrast(a, b):
    ta, tb = trials[trials.arm == a].set_index("task_id"), trials[trials.arm == b].set_index("task_id")
    shared = ta.index.intersection(tb.index)
    ma, mb = arms.loc[tuple(a.split("+"))], arms.loc[tuple(b.split("+"))]
    return {"A": a, "B": b, "tasks": len(shared),
            "A better": int((ta.loc[shared].success & ~tb.loc[shared].success.astype(bool)).sum()),
            "B better": int((tb.loc[shared].success & ~ta.loc[shared].success.astype(bool)).sum()),
            "accuracy A−B (pp)": round(100 * (ma.accuracy - mb.accuracy), 1),
            "tokens/success A vs B": f"{ma['tokens per verified success'] / mb['tokens per verified success'] - 1:+.0%}",
            "p50 A vs B": f"{ma['p50 ms'] / mb['p50 ms'] - 1:+.0%}"}

representation = pd.DataFrame([contrast(f"{a}+{d}", f"{b}+{d}") for d in DECIDERS for a, b in (("P", "H"), ("P", "M"), ("H", "M"))])
decision_pairs = [("none", "jevmodel"), ("none", "clef-ollama"), ("none", "consensus"), ("jevmodel", "clef-ollama")]
decision = pd.DataFrame([contrast(f"{r}+{a}", f"{r}+{b}") for r in REPS for a, b in decision_pairs])
print("Representation: plain prompt vs Rosetta, within each decision mode"); display(representation)
print("Decision layer: without vs with, and Jev vs clef, within each representation"); display(decision)"""),
    md("## 4. Decision providers\n\n### On the usefulness tasks"),
    code("""ud = q("SELECT * FROM usefulness_decisions WHERE run_path=?", run)
ud.groupby("provider").apply(lambda g: pd.Series({
    "tasks": len(g), "ACCEPT": (g.outcome == "ACCEPT").sum(), "NO_FIT": (g.outcome == "NO_FIT").sum(),
    "code → code_change": f"{((g.kind == 'code') & (g.route == 'code_change')).sum()}/{(g.kind == 'code').sum()}",
    "no-code → NO_FIT": f"{((g.kind == 'no_code') & (g.outcome == 'NO_FIT')).sum()}/{(g.kind == 'no_code').sum()}",
    "input tokens": g.input_tokens.sum(), "p50 ms": round(g.decision_ms.median()),
}), include_groups=False)"""),
    md("### On the routing smoke corpus (32 cases, author labels, placeholder thresholds)"),
    code("""dc = q("SELECT d.*, r.path FROM decision_cases d JOIN runs r ON r.path = d.run_path WHERE r.live = 1")
def quality(g):
    fits = g[g.label_fits == 1]
    eligible = fits[fits.selected.notna()]
    called = g[g.p_fit.notna()]
    return pd.Series({
        "cases": len(g), "top-1 route": f"{(eligible.selected == eligible.label_route).sum()}/{len(eligible)}",
        "Brier (route_fits)": round(((called.p_fit - called.label_fits) ** 2).mean(), 4),
        "false accepts": int(((g.label_fits == 0) & (g.outcome == "ACCEPT")).sum()),
        "abstain": int((g.outcome == "ABSTAIN").sum()), "input tokens": int(g.input_tokens.sum()),
        "p50 ms": round(called.decision_ms.median()),
    })
dc.groupby(["provider", "question_set", "run_path"]).apply(quality, include_groups=False)"""),
    code("""latest = dc[dc.question_set == dc.question_set.max()]
fig, ax = plt.subplots(figsize=(9, 3.2))
groups = [(1, "labelled: a route fits"), (0, "labelled: no route fits")]
for i, provider in enumerate(sorted(latest.provider.unique())):
    for j, (label, name) in enumerate(groups):
        p = latest[(latest.provider == provider) & (latest.label_fits == label)].p_fit.dropna()
        y = j + (i - 0.5) * 0.28
        ax.scatter(p, [y] * len(p), s=46, color=SERIES[i], alpha=0.85, edgecolors=SURFACE, linewidths=1.5, zorder=3,
                   label=provider if j == 0 else None)
ax.axvline(0.7, color=MUTED, linewidth=1, linestyle="--"); ax.axvline(0.3, color=MUTED, linewidth=1, linestyle="--")
ax.text(0.7, 1.55, " accept ≥ 0.7", color=INK2, fontsize=8); ax.text(0.3, 1.55, " no-fit ≤ 0.3", color=INK2, fontsize=8)
ax.set_yticks([0, 1], [name for _, name in groups]); ax.set_ylim(-0.6, 1.8); ax.set_xlim(0, 1)
ax.set_xlabel("route_fits probability (yes)")
ax.set_title(f"route_fits by label, question set {latest.question_set.max()}", loc="left")
ax.grid(axis="y", visible=False); ax.legend(loc="center left", bbox_to_anchor=(1.0, 0.5))
plt.tight_layout(); plt.show()"""),
    md("## 5. Probes and receipts"),
    code("""display(q("SELECT run_path, provider, requested_model, served_model, http_status, input_tokens, tokens_remaining, round(elapsed_ms) AS ms, error_json FROM probes ORDER BY run_path"))
q("SELECT mode, provider, cost_basis, COUNT(*) AS receipts, SUM(verified_success) AS verified FROM receipts GROUP BY mode, provider, cost_basis ORDER BY mode, provider")"""),
    md("""## 6. Reading these results

- **Ceiling.** On these 18 tasks every arm verified 18/18, so accuracy cannot separate the arms; the tasks are too easy for
  `kimi-k2.7-code:cloud`, and the baseline contract already makes the generator decline no-code requests.
- **Cost of a decision layer.** With nothing to gain in accuracy, the decision calls only add tokens and time here. A decision
  layer can pay off only where it avoids expensive work or catches failures the baseline misses — which needs harder tasks,
  costlier generation, or no-code requests the generator would otherwise act on.
- **Representation.** The Rosetta packet (M) used the fewest tokens per verified success in this run, but this is one
  temperature-0 sample per prompt; treat it as a lead to replicate, not a finding.
- **Next evidence needed.** Independent gold labels for `routing_v1`, thresholds calibrated on its calibration split and
  frozen, then held-out runs; and a harder usefulness corpus where the arms can actually differ."""),
]
nb = nbformat.v4.new_notebook(cells=cells, metadata={"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}})
client = NotebookClient(nb, timeout=180, kernel_name="python3", resources={"metadata": {"path": str(nb_dir)}})
client.execute()
nbformat.write(nb, nb_dir / "decision_layer_analysis.ipynb")
errors = [o for c in nb.cells if c.cell_type == "code" for o in c.get("outputs", []) if o.get("output_type") == "error"]
print(f"wrote {nb_dir / 'decision_layer_analysis.ipynb'}; cells {len(nb.cells)}; errors {len(errors)}")
for e in errors:
    print(e["ename"], e["evalue"])
