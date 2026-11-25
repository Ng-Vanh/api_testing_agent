import argparse
import json
from pathlib import Path

from app.config import DATA_DIR, TargetProfile
from app.engine.preflight import check
from app.engine.spec import analyze
from app.runs import load_report, run


def main():
    parser = argparse.ArgumentParser(description="API Testing Tool — OpenAPI to report")
    commands = parser.add_subparsers(dest="command", required=True)
    spec = commands.add_parser("spec", help="Validate and normalize OpenAPI offline")
    spec.add_argument("path", type=Path)
    preflight = commands.add_parser("preflight", help="Check a trusted local target profile")
    preflight.add_argument("profile", type=Path)
    preflight.add_argument("--spec", type=Path, required=True)
    run_cmd = commands.add_parser("run", help="Run one read-only operation and export its report")
    run_cmd.add_argument("--spec", type=Path, required=True)
    run_cmd.add_argument("--profile", type=Path, required=True)
    run_cmd.add_argument("--operation", required=True)
    run_cmd.add_argument("--output", type=Path, default=DATA_DIR)
    show = commands.add_parser("show", help="Read an existing report without sending requests")
    show.add_argument("run_id")
    show.add_argument("--output", type=Path, default=DATA_DIR)
    args = parser.parse_args()
    try:
        if args.command == "spec":
            endpoints = analyze(args.path)
            print(
                json.dumps(
                    {
                        "operation_count": len(endpoints),
                        "operations": [e.model_dump() for e in endpoints],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        elif args.command == "run":
            report = run(args.spec, TargetProfile.load(args.profile), args.operation, args.output)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return {"PASS": 0, "FAIL": 2, "UNKNOWN": 3, "BLOCKED": 4, "ERROR": 5, "SKIPPED": 6}[
                report["verdict"]
            ]
        elif args.command == "show":
            print(json.dumps(load_report(args.output, args.run_id), ensure_ascii=False, indent=2))
        else:
            analyze(args.spec)
            result = check(TargetProfile.load(args.profile))
            print(result.model_dump_json(indent=2))
            return 0 if result.ready else 1
    except (ValueError, OSError) as exc:
        parser.exit(1, f"{exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
