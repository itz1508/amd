"""Benchmark case scoring.

Applies grading methods from fixture definitions to determine whether an
execution result matches the expected result. Returns a normalized
:class:`CaseResult` with pass/fail, score, and normalized values.
"""

from __future__ import annotations

import math
import re
from typing import Any, Optional

from .models import CaseResult, Fixture


def _normalize_expected(expected: Any) -> Any:
    """Best-effort normalization of expected values for comparison."""
    if expected is None:
        return None
    if isinstance(expected, bool):
        return expected
    if isinstance(expected, (int, float)):
        return expected
    text = str(expected).strip().lower()
    if text in {"true", "false"}:
        return text == "true"
    try:
        if "." in text or "e" in text:
            return float(text)
        return int(text)
    except ValueError:
        return text


def _normalize_actual(result: Any) -> Any:
    """Normalize actual output from the executor."""
    if result is None:
        return None
    if isinstance(result, bool):
        return result
    if isinstance(result, (int, float)):
        return result
    if isinstance(result, dict):
        if "value" in result and len(result) == 1:
            return _normalize_actual(result["value"])
        return result
    text = str(result).strip().lower()
    if text in {"true", "false"}:
        return text == "true"
    try:
        if "." in text or "e" in text:
            return float(text)
        return int(text)
    except ValueError:
        return text


def _score_exact_match(expected: Any, actual: Any) -> float:
    return 1.0 if expected == actual else 0.0


def _score_numeric_equivalence(expected: Any, actual: Any) -> float:
    norm_expected = _normalize_expected(expected)
    norm_actual = _normalize_actual(actual)
    if norm_expected is None or norm_actual is None:
        return 1.0 if expected == actual else 0.0
    try:
        if isinstance(norm_expected, (int, float)) and isinstance(norm_actual, (int, float)):
            return 1.0 if math.isclose(float(norm_expected), float(norm_actual), rel_tol=1e-6, abs_tol=0.0) else 0.0
    except (TypeError, ValueError):
        pass
    return 1.0 if str(expected).strip().lower() == str(actual).strip().lower() else 0.0


def _score_semantic_similarity(expected: Any, actual: Any) -> float:
    expected_text = str(expected).strip().lower()
    actual_text = str(actual).strip().lower()
    if not expected_text or not actual_text:
        return 0.0
    expected_words = set(re.findall(r"\w+", expected_text))
    actual_words = set(re.findall(r"\w+", actual_text))
    if not expected_words:
        return 0.0
    intersection = expected_words & actual_words
    recall = len(intersection) / len(expected_words)
    precision = len(intersection) / max(1, len(actual_words))
    if precision + recall == 0:
        return 0.0
    return 2 * (precision * recall) / (precision + recall)


def score_case(fixture: Fixture, execution_result: Any) -> CaseResult:
    """Score a single fixture execution result."""
    expected = fixture.expected_result
    expected_norm = _normalize_expected(expected)
    actual_norm = _normalize_actual(execution_result.output if hasattr(execution_result, "output") else execution_result)
    actual = getattr(execution_result, "output", execution_result)

    grading_method = fixture.grading_method or "exact_match"
    if grading_method == "numeric_equivalence":
        passed = _score_numeric_equivalence(expected, actual_norm) >= 1.0
        score = _score_numeric_equivalence(expected, actual_norm)
    elif grading_method == "semantic_similarity":
        raw_score = _score_semantic_similarity(expected, actual)
        passed = raw_score >= 0.8
        score = raw_score
    else:
        passed = _score_exact_match(expected_norm, actual_norm) >= 1.0
        score = _score_exact_match(expected_norm, actual_norm)

    if not getattr(execution_result, "success", True):
        passed = False
        score = 0.0

    return CaseResult(
        suite_id=fixture.suite_id,
        fixture_id=fixture.fixture_id,
        capability_id=fixture.task_category,
        run_index=1,
        prompt=fixture.prompt,
        expected_result=expected,
        actual_result=actual,
        normalized_expected=expected_norm,
        normalized_actual=actual_norm,
        passed=passed,
        score=float(score),
        grading_method=grading_method,
        error_code=getattr(execution_result, "error_code", None),
        error_message=getattr(execution_result, "error_message", None),
        latency_ms=float(getattr(execution_result, "latency_ms", 0.0)),
        tokens_input=int(getattr(execution_result, "tokens_input", 0)),
        tokens_output=int(getattr(execution_result, "tokens_output", 0)),
        remote=bool(getattr(execution_result, "remote", False)),
        execution_mode="deterministic_tool",
        metadata=getattr(execution_result, "metadata", {}),
    )