"""Benchmark comparison logic.

Compares a candidate run record against a baseline run record to produce a
machine-readable comparison report with regression thresholds and overall
status.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .models import ComparisonReport, RunRecord, SuiteComparison, SuiteRunSummary


def _summaries_by_suite(run: RunRecord) -> Dict[str, SuiteRunSummary]:
    return {summary.suite_id: summary for summary in run.suites}


def _regression_threshold(metric_delta: float, baseline_value: float) -> bool:
    # Treat deltas as regression candidates if baseline > 0 and delta is negative.
    if baseline_value <= 0:
        return False
    return metric_delta < 0


def compare_runs(
    baseline: RunRecord,
    candidate: RunRecord,
    *,
    accuracy_threshold: float = -0.01,
    latency_threshold: float = 0.15,
    failure_rate_threshold: float = 0.02,
) -> ComparisonReport:
    """Compare two run records and return a structured comparison report."""
    baseline_map = _summaries_by_suite(baseline)
    candidate_map = _summaries_by_suite(candidate)
    common_suite_ids = sorted(set(baseline_map) & set(candidate_map))
    suites: List[SuiteComparison] = []
    overall_regressions = 0

    for suite_id in common_suite_ids:
        b = baseline_map[suite_id]
        c = candidate_map[suite_id]
        accuracy_delta = round(c.accuracy - b.accuracy, 6)
        latency_delta_ms = round(c.mean_latency_ms - b.mean_latency_ms, 6)
        failure_rate_delta = round(c.failure_rate - b.failure_rate, 6)

        regressions: List[str] = []
        improvements: List[str] = []

        if _regression_threshold(accuracy_delta, b.accuracy) and accuracy_delta < accuracy_threshold:
            regressions.append(f"accuracy regressed by {accuracy_delta:+.4f}")
        elif accuracy_delta > 0:
            improvements.append(f"accuracy improved by {accuracy_delta:+.4f}")

        if latency_delta_ms > latency_threshold * max(b.mean_latency_ms, 1e-6):
            regressions.append(f"latency increased by {latency_delta_ms:+.2f}ms")
        elif latency_delta_ms < 0:
            improvements.append(f"latency improved by {latency_delta_ms:+.2f}ms")

        if _regression_threshold(-failure_rate_delta, b.failure_rate) and failure_rate_delta > failure_rate_threshold:
            regressions.append(f"failure rate increased by {failure_rate_delta:+.4f}")
        elif failure_rate_delta < 0:
            improvements.append(f"failure rate improved by {failure_rate_delta:+.4f}")

        status = "pass"
        if regressions:
            status = "regression"
            overall_regressions += 1

        suites.append(
            SuiteComparison(
                suite_id=suite_id,
                baseline_accuracy=b.accuracy,
                candidate_accuracy=c.accuracy,
                accuracy_delta=accuracy_delta,
                baseline_mean_latency_ms=b.mean_latency_ms,
                candidate_mean_latency_ms=c.mean_latency_ms,
                latency_delta_ms=latency_delta_ms,
                baseline_failure_rate=b.failure_rate,
                candidate_failure_rate=c.failure_rate,
                failure_rate_delta=failure_rate_delta,
                regressions=regressions,
                improvements=improvements,
                status=status,
            )
        )

    overall_status = "pass" if overall_regressions == 0 else "regression"
    return ComparisonReport(
        baseline_run_id=baseline.run_id,
        candidate_run_id=candidate.run_id,
        suites=suites,
        overall_status=overall_status,
    )