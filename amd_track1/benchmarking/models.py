"""Benchmarking domain models.

Provides immutable dataclasses for benchmark suites, fixtures, case results,
run summaries, and comparison deltas. These models are used across the
benchmarking loader, runner, scorer, metrics, reporting, and CLI modules.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Fixture and suite models
# ---------------------------------------------------------------------------

@dataclass
class Fixture:
    """Single benchmark case loaded from a JSONL fixture file."""

    fixture_id: str
    suite_id: str
    task_category: str
    prompt: str
    expected_result: Any = None
    grading_method: str = "exact_match"
    difficulty: str = "basic"
    tags: List[str] = field(default_factory=list)
    allowed_execution_modes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> Fixture:
        return cls(
            fixture_id=str(payload.get("fixture_id", "")),
            suite_id=str(payload.get("suite_id", "")),
            task_category=str(payload.get("task_category", "")),
            prompt=str(payload.get("prompt", "")),
            expected_result=payload.get("expected_result"),
            grading_method=str(payload.get("grading_method", "exact_match")),
            difficulty=str(payload.get("difficulty", "basic")),
            tags=[str(tag) for tag in payload.get("tags", [])],
            allowed_execution_modes=[str(mode) for mode in payload.get("allowed_execution_modes", [])],
            metadata={k: v for k, v in payload.items() if k not in {
                "fixture_id", "suite_id", "task_category", "prompt", "expected_result",
                "grading_method", "difficulty", "tags", "allowed_execution_modes",
            }},
        )


@dataclass
class SuiteManifest:
    """Benchmark suite configuration loaded from a JSON manifest."""

    suite_id: str
    version: str = "1.0.0"
    capability_ids: List[str] = field(default_factory=list)
    description: str = ""
    fixture_path: str = ""
    scorer_ids: List[str] = field(default_factory=list)
    repetitions: int = 1
    warmup_runs: int = 0
    timeout_ms: int = 10000
    random_seed: Optional[int] = None
    environment_requirements: Dict[str, Any] = field(default_factory=dict)
    metrics: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> SuiteManifest:
        return cls(
            suite_id=str(payload.get("suite_id", "")),
            version=str(payload.get("version", "1.0.0")),
            capability_ids=[str(c) for c in payload.get("capability_ids", [])],
            description=str(payload.get("description", "")),
            fixture_path=str(payload.get("fixture_path", "")),
            scorer_ids=[str(s) for s in payload.get("scorer_ids", [])],
            repetitions=int(payload.get("repetitions", 1)),
            warmup_runs=int(payload.get("warmup_runs", 0)),
            timeout_ms=int(payload.get("timeout_ms", 10000)),
            random_seed=payload.get("random_seed"),
            environment_requirements=dict(payload.get("environment_requirements", {}) or {}),
            metrics=[str(m) for m in payload.get("metrics", [])],
            metadata={k: v for k, v in payload.items() if k not in {
                "suite_id", "version", "capability_ids", "description", "fixture_path",
                "scorer_ids", "repetitions", "warmup_runs", "timeout_ms", "random_seed",
                "environment_requirements", "metrics",
            }},
        )


# ---------------------------------------------------------------------------
# Result and run record models
# ---------------------------------------------------------------------------

@dataclass
class CaseResult:
    """Result of executing a single fixture case."""

    suite_id: str
    fixture_id: str
    capability_id: str
    run_index: int
    prompt: str
    expected_result: Any = None
    actual_result: Any = None
    normalized_expected: Any = None
    normalized_actual: Any = None
    passed: bool = False
    score: float = 0.0
    grading_method: str = "exact_match"
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    latency_ms: float = 0.0
    tokens_input: int = 0
    tokens_output: int = 0
    remote: bool = False
    execution_mode: str = "deterministic_tool"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suite_id": self.suite_id,
            "fixture_id": self.fixture_id,
            "capability_id": self.capability_id,
            "run_index": self.run_index,
            "prompt": self.prompt,
            "expected_result": self.expected_result,
            "actual_result": self.actual_result,
            "normalized_expected": self.normalized_expected,
            "normalized_actual": self.normalized_actual,
            "passed": self.passed,
            "score": self.score,
            "grading_method": self.grading_method,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "latency_ms": self.latency_ms,
            "tokens_input": self.tokens_input,
            "tokens_output": self.tokens_output,
            "remote": self.remote,
            "execution_mode": self.execution_mode,
            "metadata": self.metadata,
        }


@dataclass
class SuiteRunSummary:
    """Aggregated summary for one suite execution."""

    suite_id: str
    capability_ids: List[str]
    total_cases: int = 0
    passed_cases: int = 0
    failed_cases: int = 0
    error_cases: int = 0
    accuracy: float = 0.0
    mean_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    total_tokens_input: int = 0
    total_tokens_output: int = 0
    remote_tokens: int = 0
    estimated_cost: float = 0.0
    failure_rate: float = 0.0
    repetition_count: int = 1
    warmup_count: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    environment: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suite_id": self.suite_id,
            "capability_ids": self.capability_ids,
            "total_cases": self.total_cases,
            "passed_cases": self.passed_cases,
            "failed_cases": self.failed_cases,
            "error_cases": self.error_cases,
            "accuracy": self.accuracy,
            "mean_latency_ms": self.mean_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "total_tokens_input": self.total_tokens_input,
            "total_tokens_output": self.total_tokens_output,
            "remote_tokens": self.remote_tokens,
            "estimated_cost": self.estimated_cost,
            "failure_rate": self.failure_rate,
            "repetition_count": self.repetition_count,
            "warmup_count": self.warmup_count,
            "timestamp": self.timestamp,
            "environment": self.environment,
            "metadata": self.metadata,
        }


@dataclass
class RunRecord:
    """Top-level run record that can be serialized to JSON."""

    run_id: str
    command: str
    suites: List[SuiteRunSummary]
    case_results: List[CaseResult]
    configuration: Dict[str, Any] = field(default_factory=dict)
    environment: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = "ok"
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "run_id": self.run_id,
            "command": self.command,
            "status": self.status,
            "timestamp": self.timestamp,
            "configuration": self.configuration,
            "environment": self.environment,
            "suites": [suite.to_dict() for suite in self.suites],
            "case_results": [case.to_dict() for case in self.case_results],
            "metadata": self.metadata,
        }
        if self.error:
            payload["error"] = self.error
        return payload

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=False)


# ---------------------------------------------------------------------------
# Comparison models
# ---------------------------------------------------------------------------

@dataclass
class SuiteComparison:
    """Delta between two suite runs for one suite."""

    suite_id: str
    baseline_accuracy: float = 0.0
    candidate_accuracy: float = 0.0
    accuracy_delta: float = 0.0
    baseline_mean_latency_ms: float = 0.0
    candidate_mean_latency_ms: float = 0.0
    latency_delta_ms: float = 0.0
    baseline_failure_rate: float = 0.0
    candidate_failure_rate: float = 0.0
    failure_rate_delta: float = 0.0
    regressions: List[str] = field(default_factory=list)
    improvements: List[str] = field(default_factory=list)
    status: str = "pass"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suite_id": self.suite_id,
            "baseline_accuracy": self.baseline_accuracy,
            "candidate_accuracy": self.candidate_accuracy,
            "accuracy_delta": self.accuracy_delta,
            "baseline_mean_latency_ms": self.baseline_mean_latency_ms,
            "candidate_mean_latency_ms": self.candidate_mean_latency_ms,
            "latency_delta_ms": self.latency_delta_ms,
            "baseline_failure_rate": self.baseline_failure_rate,
            "candidate_failure_rate": self.candidate_failure_rate,
            "failure_rate_delta": self.failure_rate_delta,
            "regressions": self.regressions,
            "improvements": self.improvements,
            "status": self.status,
        }


@dataclass
class ComparisonReport:
    """Top-level comparison result across multiple suites."""

    baseline_run_id: str
    candidate_run_id: str
    suites: List[SuiteComparison]
    overall_status: str = "pass"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "baseline_run_id": self.baseline_run_id,
            "candidate_run_id": self.candidate_run_id,
            "overall_status": self.overall_status,
            "timestamp": self.timestamp,
            "suites": [suite.to_dict() for suite in self.suites],
            "metadata": self.metadata,
        }