import argparse
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bench")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run")

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
    if args.command == "export" and args.export_format == "xlsx":
        return _run_export_xlsx(Path(args.csv), Path(args.out))
    if args.command == "export" and args.export_format == "sheets":
        return _run_export_sheets(Path(args.csv), args.sheet_name)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
