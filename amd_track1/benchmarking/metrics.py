"""Benchmark metrics aggregation.

Computes suite-level and run-level aggregate statistics from case results.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional

from .models import CaseResult, SuiteRunSummary


def _mean(values: List[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _p95(values: List[float]) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    sorted_values = sorted(values)
    idx = math.ceil(0.95 * len(sorted_values)) - 1
    idx = max(0, min(idx, len(sorted_values) - 1))
    return sorted_values[idx]


@dataclass
class SuiteMetrics:
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

    @classmethod
    def from_case_results(cls, suite_id: str, capability_ids: List[str], cases: List[CaseResult], cost_per_remote_token: float = 0.0) -> SuiteMetrics:
        total_cases = len(cases)
        passed_cases = sum(1 for c in cases if c.passed and not c.error_code)
        failed_cases = sum(1 for c in cases if not c.passed and not c.error_code)
        error_cases = sum(1 for c in cases if c.error_code)
        accuracy = passed_cases / total_cases if total_cases else 0.0
        latencies = [c.latency_ms for c in cases]
        mean_latency_ms = _mean(latencies)
        p95_latency_ms = _p95(latencies)
        total_tokens_input = sum(c.tokens_input for c in cases)
        total_tokens_output = sum(c.tokens_output for c in cases)
        remote_tokens = sum(c.tokens_output for c in cases if c.remote)
        estimated_cost = remote_tokens * cost_per_remote_token
        failure_rate = (failed_cases + error_cases) / total_cases if total_cases else 0.0
        return cls(
            suite_id=suite_id,
            capability_ids=capability_ids,
            total_cases=total_cases,
            passed_cases=passed_cases,
            failed_cases=failed_cases,
            error_cases=error_cases,
            accuracy=accuracy,
            mean_latency_ms=mean_latency_ms,
            p95_latency_ms=p95_latency_ms,
            total_tokens_input=total_tokens_input,
            total_tokens_output=total_tokens_output,
            remote_tokens=remote_tokens,
            estimated_cost=estimated_cost,
            failure_rate=failure_rate,
        )

    def to_summary(self, repetition_count: int = 1, warmup_count: int = 0, environment: Optional[dict] = None, metadata: Optional[dict] = None) -> SuiteRunSummary:
        return SuiteRunSummary(
            suite_id=self.suite_id,
            capability_ids=self.capability_ids,
            total_cases=self.total_cases,
            passed_cases=self.passed_cases,
            failed_cases=self.failed_cases,
            error_cases=self.error_cases,
            accuracy=self.accuracy,
            mean_latency_ms=self.mean_latency_ms,
            p95_latency_ms=self.p95_latency_ms,
            total_tokens_input=self.total_tokens_input,
            total_tokens_output=self.total_tokens_output,
            remote_tokens=self.remote_tokens,
            estimated_cost=self.estimated_cost,
            failure_rate=self.failure_rate,
            repetition_count=repetition_count,
            warmup_count=warmup_count,
            environment=environment or {},
            metadata=metadata or {},
        )