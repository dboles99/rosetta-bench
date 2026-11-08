import argparse
import json
import sys
from pathlib import Path

from rosetta_bench.export_xlsx import export_to_xlsx


def _run_export_xlsx(csv_path: Path, out_path: Path) -> int:
    export_to_xlsx(csv_path, out_path)
    print(f"wrote {out_path}")
    return 0


def _run_export_sheets(csv_path: Path, sheet_name: str) -> int:
    import os

    from rosetta_bench.export_sheets import GSpreadClient, export_to_sheets

    service_account_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not service_account_path:
        print("GOOGLE_SERVICE_ACCOUNT_JSON is not set", file=sys.stderr)
        return 1
    client = GSpreadClient(service_account_path)
    export_to_sheets(csv_path, sheet_name, client)
    print(f"wrote to Google Sheet '{sheet_name}'")
    return 0


def _run_bench(args: argparse.Namespace) -> int:
    # Wiring live runners (Claude/Azure OpenAI/Azure Translation/Ollama) requires
    # real credentials and is exercised manually per-tool, not by this CLI's
    # automated test suite. Construct the harness call yourself using
    # rosetta_bench.harness.run_trial with the concrete SDK/HTTP client adapters
    # from each runner module.
    print(
        "`bench run` is not automated in v1 -- requires live credentials for "
        "each tool. Use rosetta_bench.harness.run_trial directly with the "
        "concrete client adapters (ClaudeRunner + AnthropicSDKClient, etc.).",
        file=sys.stderr,
    )
    return 1


def _run_experiment(config_path: Path, out_dir: Path) -> int:
    from rosetta_bench.experiment.config import ConfigError, load_config
    from rosetta_bench.experiment.runner import run_experiment

    try:
        config = load_config(config_path)
        run_experiment(config, out_dir)
    except (ConfigError, FileExistsError) as exc:
        print(f"experiment not run: {exc}", file=sys.stderr)
        return 2
    print(f"wrote {out_dir}")
    return 0


def _report_experiment(run_dir: Path) -> int:
    from rosetta_bench.report import write_report

    print(f"wrote {write_report(run_dir)}")
    return 0


def _decision_transport(args, profile):
    """Returns (transport, api_key) or an error message. Live providers need --live,
    their key in the named environment variable, and an explicit --max-calls budget."""
    import os

    from rosetta_bench.decision.fake_provider import FakeSystemOne
    from rosetta_bench.decision.transport import BudgetTransport, FakeTransport, UrllibTransport

    if profile.name == "fake":
        transport, key = FakeTransport(FakeSystemOne()), None
    else:
        if not args.live:
            return None, None, f"provider '{profile.name}' makes network calls to {profile.endpoint}; add --live to confirm"
        key = os.environ.get(profile.api_key_env) if profile.api_key_env else None
        if profile.api_key_env and not key:
            return None, None, f"{profile.api_key_env} is not set in this environment; set it, then rerun"
        if args.max_calls is None:
            return None, None, "live runs need an explicit --max-calls budget (retries count as calls)"
        transport = UrllibTransport()
    if args.max_calls is not None:
        transport = BudgetTransport(transport, args.max_calls)
    return transport, key, None


def _decision_command(args) -> int:
    from rosetta_bench.decision.profiles import PROFILES

    if args.decision_command == "replay":
        from rosetta_bench.decision.shadow import replay_run

        report = replay_run(Path(args.run))
        print(f"replayed {report.cases} cases; mismatches: {len(report.mismatches)} {report.mismatches or ''}".rstrip())
        return 0 if not report.mismatches else 1
    if args.decision_command == "report":
        from rosetta_bench.decision.report import write_decision_report

        print(f"wrote {write_decision_report(Path(args.run))}")
        return 0

    profile = PROFILES.get(args.provider)
    if profile is None:
        print(f"unknown provider {args.provider!r}; choose from {sorted(PROFILES)}", file=sys.stderr)
        return 2
    out = Path(args.out)
    if (out / "manifest.json").exists() or (out / "probe.json").exists():
        print(f"{out} already holds results; choose a new --out directory", file=sys.stderr)
        return 2
    transport, key, error = _decision_transport(args, profile)
    if error:
        print(error, file=sys.stderr)
        return 2

    if args.decision_command == "probe":
        from rosetta_bench.decision.probe import run_probe

        probe = run_probe(profile, transport, key, Path(args.corpus), out)
        print(json.dumps({k: probe[k] for k in ("served_model", "http_status", "calls", "input_tokens", "tokens_remaining", "fields", "error")}, indent=2))
        return 0 if probe["error"] is None else 1

    from rosetta_bench.decision.shadow import run_shadow

    run_shadow(Path(args.corpus), profile, transport, out, seed=args.seed, api_key=key, live=profile.name != "fake")
    print(f"wrote {out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bench")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run")

    experiment_parser = subparsers.add_parser("experiment")
    experiment_subparsers = experiment_parser.add_subparsers(dest="experiment_command", required=True)
    experiment_run = experiment_subparsers.add_parser("run")
    experiment_run.add_argument("--config", required=True)
    experiment_run.add_argument("--out", required=True)
    experiment_report = experiment_subparsers.add_parser("report")
    experiment_report.add_argument("--run", required=True)

    decision_parser = subparsers.add_parser("decision")
    decision_subparsers = decision_parser.add_subparsers(dest="decision_command", required=True)
    for name in ("run", "probe"):
        sub = decision_subparsers.add_parser(name)
        sub.add_argument("--corpus", default="corpus/routing_smoke")
        sub.add_argument("--provider", required=True)
        sub.add_argument("--out", required=True)
        sub.add_argument("--live", action="store_true", help="confirm that this run may call a network provider")
        sub.add_argument("--max-calls", type=int, default=None)
        sub.add_argument("--seed", type=int, default=20261109)
    for name in ("replay", "report"):
        decision_subparsers.add_parser(name).add_argument("--run", required=True)

    export_parser = subparsers.add_parser("export")
    export_subparsers = export_parser.add_subparsers(dest="export_format", required=True)

    xlsx_parser = export_subparsers.add_parser("xlsx")
    xlsx_parser.add_argument("--csv", required=True)
    xlsx_parser.add_argument("--out", required=True)

    sheets_parser = export_subparsers.add_parser("sheets")
    sheets_parser.add_argument("--csv", required=True)
    sheets_parser.add_argument("--sheet-name", required=True)

    args = parser.parse_args(argv)

    if args.command == "run":
        return _run_bench(args)
    if args.command == "experiment" and args.experiment_command == "run":
        return _run_experiment(Path(args.config), Path(args.out))
    if args.command == "experiment" and args.experiment_command == "report":
        return _report_experiment(Path(args.run))
    if args.command == "decision":
        return _decision_command(args)
    if args.command == "export" and args.export_format == "xlsx":
        return _run_export_xlsx(Path(args.csv), Path(args.out))
    if args.command == "export" and args.export_format == "sheets":
        return _run_export_sheets(Path(args.csv), args.sheet_name)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
