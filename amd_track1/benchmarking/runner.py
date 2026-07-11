"""Benchmark suite runner.

Executes a full suite manifest across its fixtures and repetitions,
warmup runs, and produces a complete run record with per-suite summaries.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .loader import load_suite, load_fixtures, list_suite_ids
from .metrics import SuiteMetrics
from .models import CaseResult, RunRecord, SuiteRunSummary
from .scoring import score_case
from ..capabilities.executors import execute


@dataclass
class SuiteRunnerResult:
    run_record: RunRecord
    report: str = ""


class SuiteRunner:
    """Runs benchmark suites and returns run records."""

    def __init__(self, default_command: Optional[str] = None) -> None:
        self.default_command = default_command or "python -m amd_track1.benchmarking.cli"
        self._environment: Dict[str, Any] = {}

    def _build_environment(self) -> Dict[str, Any]:
        return {
            "python_version": self._python_version(),
        }

    def _python_version(self) -> str:
        import platform
        return f"{platform.python_implementation()} {platform.python_version()}"

    def run_suite(self, suite_id: str, *, output_dir: Optional[str] = None) -> SuiteRunnerResult:
        manifest = load_suite(suite_id)
        fixtures = load_fixtures(suite_id)
        case_results: List[CaseResult] = []
        start = time.perf_counter()
        for repetition in range(manifest.repetitions):
            is_warmup = repetition < manifest.warmup_runs
            for fixture in fixtures:
                if not is_warmup:
                    t0 = time.perf_counter()
                    execution = execute(manifest.capability_ids[0] if manifest.capability_ids else fixture.task_category, fixture.prompt)
                    latency_ms = (time.perf_counter() - t0) * 1000.0
                    case = score_case(fixture, execution)
                    case.latency_ms = latency_ms
                    case.run_index = repetition + 1
                    case.execution_mode = "deterministic_tool"
                else:
                    case = CaseResult(
                        suite_id=fixture.suite_id,
                        fixture_id=fixture.fixture_id,
                        capability_id=manifest.capability_ids[0] if manifest.capability_ids else fixture.task_category,
                        run_index=repetition + 1,
                        prompt=fixture.prompt,
                        expected_result=fixture.expected_result,
                        actual_result=None,
                        normalized_expected=fixture.expected_result,
                        normalized_actual=None,
                        passed=False,
                        score=0.0,
                        grading_method=fixture.grading_method,
                        error_code="warmup",
                        error_message="warmup run",
                        latency_ms=0.0,
                        tokens_input=0,
                        tokens_output=0,
                        remote=False,
                        execution_mode="deterministic_tool",
                        metadata={"warmup": True},
                    )
                case_results.append(case)
        suite_metrics = SuiteMetrics.from_case_results(
            suite_id=manifest.suite_id,
            capability_ids=list(manifest.capability_ids),
            cases=[c for c in case_results if c.error_code != "warmup"],
        )
        summary = suite_metrics.to_summary(
            repetition_count=max(1, manifest.repetitions - manifest.warmup_runs),
            warmup_count=manifest.warmup_runs,
            environment=self._environment,
        )
        run_id = str(uuid.uuid4())
        run_record = RunRecord(
            run_id=run_id,
            command=self.default_command,
            suites=[summary],
            case_results=case_results,
            configuration={"suite_id": suite_id},
            environment=self._environment,
            status="ok",
        )
        return SuiteRunnerResult(run_record=run_record)

    def run_all(self, *, output_dir: Optional[str] = None) -> SuiteRunnerResult:
        suite_ids = list_suite_ids()
        case_results: List[CaseResult] = []
        suites: List[SuiteRunSummary] = []
        for suite_id in suite_ids:
            result = self.run_suite(suite_id, output_dir=output_dir)
            case_results.extend(result.run_record.case_results)
            suites.extend(result.run_record.suites)
        run_id = str(uuid.uuid4())
        run_record = RunRecord(
            run_id=run_id,
            command=self.default_command,
            suites=suites,
            case_results=case_results,
            configuration={"suite_ids": suite_ids},
            environment=self._environment,
            status="ok",
        )
        return SuiteRunnerResult(run_record=run_record)