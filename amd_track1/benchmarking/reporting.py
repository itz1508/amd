"""Benchmark report generation.

Produces machine-readable and human-readable reports from run records and
comparison reports. Output formats currently supported: JSON and Markdown.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from .models import ComparisonReport, RunRecord, SuiteRunSummary


@dataclass
class BenchmarkReport:
    run_id: str
    generated_at: str
    format: str
    payload: Union[RunRecord, ComparisonReport]
    raw: str = ""

    def to_json(self, indent: int = 2) -> str:
        if isinstance(self.payload, (RunRecord, ComparisonReport)):
            return json.dumps(self.payload.to_dict(), indent=indent, sort_keys=False)
        return json.dumps(self.payload, indent=indent, sort_keys=False)

    def to_markdown(self) -> str:
        payload = self.payload
        lines = [
            f"# Benchmark Report",
            f"",
            f"- run_id: {self.run_id}",
            f"- generated_at: {self.generated_at}",
            f"- format: {self.format}",
            f"",
        ]
        if isinstance(payload, RunRecord):
            lines.extend(_render_run_record_markdown(payload))
        elif isinstance(payload, ComparisonReport):
            lines.extend(_render_comparison_markdown(payload))
        return "\n".join(lines)


def _render_run_record_markdown(run: RunRecord) -> List[str]:
    lines = [f"## Run Record", f""]
    for suite in run.suites:
        lines.extend([
            f"### {suite.suite_id}",
            f"",
            f"| Metric | Value |",
            f"| --- | --- |",
            f"| total_cases | {suite.total_cases} |",
            f"| passed_cases | {suite.passed_cases} |",
            f"| failed_cases | {suite.failed_cases} |",
            f"| error_cases | {suite.error_cases} |",
            f"| accuracy | {suite.accuracy:.4f} |",
            f"| mean_latency_ms | {suite.mean_latency_ms:.2f} |",
            f"| p95_latency_ms | {suite.p95_latency_ms:.2f} |",
            f"| total_tokens_input | {suite.total_tokens_input} |",
            f"| total_tokens_output | {suite.total_tokens_output} |",
            f"| failure_rate | {suite.failure_rate:.4f} |",
            f"",
        ])
    return lines


def _render_comparison_markdown(comparison: ComparisonReport) -> List[str]:
    lines = [
        f"## Comparison",
        f"",
        f"- overall_status: {comparison.overall_status}",
        f"- baseline_run_id: {comparison.baseline_run_id}",
        f"- candidate_run_id: {comparison.candidate_run_id}",
        f"",
    ]
    for suite in comparison.suites:
        lines.extend([
            f"### {suite.suite_id}",
            f"",
            f"- baseline_accuracy: {suite.baseline_accuracy:.4f}",
            f"- candidate_accuracy: {suite.candidate_accuracy:.4f}",
            f"- accuracy_delta: {suite.accuracy_delta:+.4f}",
            f"- latency_delta_ms: {suite.latency_delta_ms:+.2f}",
            f"- failure_rate_delta: {suite.failure_rate_delta:+.4f}",
            f"- status: {suite.status}",
        ])
        if suite.regressions:
            lines.extend([f"- regressions:"] + [f"  - {item}" for item in suite.regressions])
        if suite.improvements:
            lines.extend([f"- improvements:"] + [f"  - {item}" for item in suite.improvements])
        lines.append("")
    return lines


def build_report(run: RunRecord, fmt: str = "json") -> BenchmarkReport:
    if fmt == "markdown":
        report = BenchmarkReport(run_id=run.run_id, generated_at=datetime.now(timezone.utc).isoformat(), format="markdown", payload=run)
        report.raw = report.to_markdown()
        return report
    report = BenchmarkReport(run_id=run.run_id, generated_at=datetime.now(timezone.utc).isoformat(), format="json", payload=run)
    report.raw = report.to_json()
    return report


def build_comparison_report(comparison: ComparisonReport, fmt: str = "json") -> BenchmarkReport:
    if fmt == "markdown":
        report = BenchmarkReport(run_id=comparison.candidate_run_id, generated_at=datetime.now(timezone.utc).isoformat(), format="markdown", payload=comparison)
        report.raw = report.to_markdown()
        return report
    report = BenchmarkReport(run_id=comparison.candidate_run_id, generated_at=datetime.now(timezone.utc).isoformat(), format="json", payload=comparison)
    report.raw = report.to_json()
    return report