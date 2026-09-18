"""Local-only development harness CLI."""

import argparse
import json

from tbm.cases import generate_cases, write_cases
from tbm.runner import MODES, run_matrix, safe_project_path, verify_run


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Local scripted tool-boundary experiments")
    commands = parser.add_subparsers(dest="command", required=True)
    generate = commands.add_parser("generate")
    generate.add_argument("--output", required=True)
    run = commands.add_parser("run")
    run.add_argument("--cases", required=True)
    run.add_argument("--mode", choices=[*MODES, "all"], default="all")
    run.add_argument("--output", required=True)
    verify = commands.add_parser("verify")
    verify.add_argument("--run", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "generate":
            digest = write_cases(safe_project_path(args.output), generate_cases())
            print(f"Generated 54 scripted development cases; SHA256 {digest}")
            return 0
        if args.command == "run":
            path = safe_project_path(args.output)
            summary = run_matrix(
                safe_project_path(args.cases),
                list(MODES) if args.mode == "all" else [args.mode],
                path,
            )
            print(
                json.dumps(
                    {"executions": summary["executions"], "modes": summary["modes"]}, indent=2
                )
            )
        else:
            path = safe_project_path(args.run)
        errors = verify_run(path)
        for error in errors:
            print(error)
        if not errors:
            print("VERIFIED: complete inventory, hashes, audit pairs and independent outcomes")
        return int(bool(errors))
    except (ValueError, OSError, KeyError, TypeError):
        print("COMMAND_FAILED: invalid input, unsafe path, existing output or unavailable artifact")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
