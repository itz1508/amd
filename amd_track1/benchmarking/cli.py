"""Benchmarking CLI.

Supports commands:
- list-capabilities
- list-suites
- run-suite
- run-capability
- smoke
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from amd_track1.capabilities import list_capabilities

from .loader import list_suite_ids, load_suite, load_fixtures, validate_suite
from .reporting import build_report
from .runner import SuiteRunner
from .comparison import compare_runs
from .models import RunRecord


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m amd_track1.benchmarking.cli")
    sub = parser.add_subparsers(dest="command")
    sub.required = True

    sub.add_parser("list-capabilities")
    sub.add_parser("list-suites")

    smoke = sub.add_parser("smoke")
    smoke.add_argument("--suite", default="math-core")

    run_suite = sub.add_parser("run-suite")
    run_suite.add_argument("suite_id")
    run_suite.add_argument("--output-dir")
    run_suite.add_argument("--format", choices=["json", "markdown"], default="json")

    run_cap = sub.add_parser("run-capability")
    run_cap.add_argument("capability_id")
    run_cap.add_argument("--output-dir")
    run_cap.add_argument("--format", choices=["json", "markdown"], default="json")

    compare = sub.add_parser("compare")
    compare.add_argument("baseline")
    compare.add_argument("candidate")

    validate = sub.add_parser("validate")
    validate.add_argument("suite_id")

    return parser


def _write_output(payload: Dict[str, Any], output_dir: Optional[str], filename: str) -> Optional[str]:
    if output_dir:
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)
        out = path / filename
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return str(out)
    return None


def main(argv: Optional[Sequence[str]] = None, output_stream: Optional[Any] = None) -> Dict[str, Any]:
    parser = build_parser()
    args = parser.parse_args(list(argv or []))

    if args.command == "list-capabilities":
        capabilities = list_capabilities()
        payload = {"status": "ok", "count": len(capabilities), "capabilities": capabilities}
        if output_stream is not None:
            output_stream.write(json.dumps(payload, indent=2))
        return payload

    if args.command == "list-suites":
        suites = list_suite_ids()
        payload = {"status": "ok", "count": len(suites), "suites": suites}
        if output_stream is not None:
            output_stream.write(json.dumps(payload, indent=2))
        return payload

    if args.command == "smoke":
        runner = SuiteRunner()
        result = runner.run_suite(args.suite)
        report = build_report(result.run_record, fmt="json")
        payload = {
            "status": "ok",
            "suite_id": args.suite,
            "suite_count": len(result.run_record.suites),
            "run_id": result.run_record.run_id,
            "accuracy": result.run_record.suites[0].accuracy if result.run_record.suites else 0.0,
            "report": report.raw,
        }
        if output_stream is not None:
            output_stream.write(json.dumps(payload, indent=2))
        return payload

    if args.command == "run-suite":
        runner = SuiteRunner()
        result = runner.run_suite(args.suite_id, output_dir=args.output_dir)
        report = build_report(result.run_record, fmt=args.format)
        payload = result.run_record.to_dict()
        payload["report"] = report.raw
        saved = _write_output(payload, args.output_dir, f"{args.suite_id}-run.json")
        if saved:
            payload["output_file"] = saved
        if output_stream is not None:
            output_stream.write(report.raw)
        return payload

    if args.command == "run-capability":
        capabilities = {c["capability_id"]: c for c in list_capabilities()}
        capability = capabilities.get(args.capability_id)
        if not capability:
            payload = {"status": "error", "message": f"unknown capability: {args.capability_id}"}
            if output_stream is not None:
                output_stream.write(json.dumps(payload, indent=2))
            return payload
        associated_suites = capability.get("benchmark_suites", [])
        if not associated_suites:
            payload = {"status": "ok", "capability_id": args.capability_id, "suites": []}
            if output_stream is not None:
                output_stream.write(json.dumps(payload, indent=2))
            return payload
        first = associated_suites[0]
        runner = SuiteRunner()
        result = runner.run_suite(first, output_dir=args.output_dir)
        report = build_report(result.run_record, fmt=args.format)
        payload = result.run_record.to_dict()
        payload["capability_id"] = args.capability_id
        payload["report"] = report.raw
        saved = _write_output(payload, args.output_dir, f"{args.capability_id}-run.json")
        if saved:
            payload["output_file"] = saved
        if output_stream is not None:
            output_stream.write(report.raw)
        return payload

    if args.command == "compare":
        with open(args.baseline, "r", encoding="utf-8") as handle:
            baseline = RunRecord(**json.load(handle))
        with open(args.candidate, "r", encoding="utf-8") as handle:
            candidate = RunRecord(**json.load(handle))
        comparison = compare_runs(baseline, candidate)
        from .reporting import build_comparison_report
        report = build_comparison_report(comparison, fmt="json")
        payload = comparison.to_dict()
        payload["report"] = report.raw
        if output_stream is not None:
            output_stream.write(report.raw)
        return payload

    if args.command == "validate":
        issues = validate_suite(args.suite_id)
        payload = {"status": "ok" if not issues else "issues", "suite_id": args.suite_id, "issues": issues}
        if output_stream is not None:
            output_stream.write(json.dumps(payload, indent=2))
        return payload

    payload = {"status": "error", "message": "unsupported command"}
    if output_stream is not None:
        output_stream.write(json.dumps(payload, indent=2))
    return payload


if __name__ == "__main__":
    result = main(sys.argv[1:])
    print(json.dumps(result, indent=2))