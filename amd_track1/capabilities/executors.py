"""Capability executor adapters.

This module provides a uniform ``execute(capability_id, prompt, **kwargs)``
interface that the benchmarking framework can call without needing to know
the internal implementation of each capability.

Each adapter is intentionally lightweight and deterministic where possible.
The adapters wrap the existing tools in ``amd_track1.tools`` and return a
structured :class:`ExecutionResult` so the runner can score, log, and
aggregate results uniformly.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from amd_track1.tools.arithmetic_evaluator import arithmetic_evaluator
from amd_track1.tools.sentiment_validator import SentimentValidator
from amd_track1.tools.ner_validator import NamedEntityValidator
from amd_track1.tools.summary_checker import SummaryConstraintChecker
from amd_track1.tools.code_checker import CodeSyntaxChecker
from amd_track1.tools.logic_checker import LogicConsistencyChecker
from amd_track1.tools.json_validator import JSONValidator


@dataclass
class ExecutionResult:
    """Structured result returned by every capability executor."""

    success: bool
    output: Any = None
    normalized_output: Any = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    tokens_input: int = 0
    tokens_output: int = 0
    remote: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "normalized_output": self.normalized_output,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "tokens_input": self.tokens_input,
            "tokens_output": self.tokens_output,
            "remote": self.remote,
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NUMBER_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
    "hundred": 100, "thousand": 1000, "million": 1000000,
}


def _approx_tokens(text: str) -> int:
    """Cheap deterministic token estimate (whitespace split)."""
    if not text:
        return 0
    return max(1, len(re.findall(r"\S+", text)))


def _extract_expression(prompt: str) -> Optional[str]:
    """Extract a mathematical expression from a natural-language prompt."""
    if not prompt:
        return None
    text = prompt.lower()
    text = re.sub(r"multiplied by", "*", text)
    text = re.sub(r"times", "*", text)
    text = re.sub(r"divided by", "/", text)
    text = re.sub(r"to the power of", "**", text)
    text = re.sub(r"plus", "+", text)
    text = re.sub(r"minus", "-", text)
    match = re.search(r"([0-9][0-9\s\+\-\*\/\^\.\(\)%]*[0-9\)])", text)
    if match:
        return match.group(1).strip()
    return None


def _normalize_number(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    try:
        return float(text)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Capability executors
# ---------------------------------------------------------------------------

def execute_mathematical_reasoning(prompt: str, **_: Any) -> ExecutionResult:
    expression = _extract_expression(prompt)
    if not expression:
        return ExecutionResult(
            success=False,
            error_code="no_expression",
            error_message="could not extract arithmetic expression from prompt",
            tokens_input=_approx_tokens(prompt),
        )
    result = arithmetic_evaluator.calculate(expression)
    if not result.success:
        return ExecutionResult(
            success=False,
            error_code=result.error_code,
            error_message=result.error_message,
            tokens_input=_approx_tokens(prompt),
            metadata={"expression": expression},
        )
    return ExecutionResult(
        success=True,
        output=result.value,
        normalized_output=_normalize_number(result.value),
        tokens_input=_approx_tokens(prompt),
        tokens_output=1,
        metadata={"expression": expression, "normalized": result.normalized_expression},
    )


def execute_factual_knowledge(prompt: str, **_: Any) -> ExecutionResult:
    # Deterministic stub: returns the prompt verbatim so the scorer can
    # compare against the expected_result field of the fixture.
    return ExecutionResult(
        success=True,
        output=prompt,
        normalized_output=prompt.strip().lower(),
        tokens_input=_approx_tokens(prompt),
        tokens_output=_approx_tokens(prompt),
        metadata={"mode": "deterministic_stub"},
    )


def execute_sentiment_classification(prompt: str, **_: Any) -> ExecutionResult:
    validator = SentimentValidator()
    valid, normalized, error = validator.validate_sentiment_output(prompt)
    if not valid:
        return ExecutionResult(
            success=False,
            error_code="invalid_sentiment",
            error_message=error,
            tokens_input=_approx_tokens(prompt),
        )
    return ExecutionResult(
        success=True,
        output=normalized,
        normalized_output=normalized,
        tokens_input=_approx_tokens(prompt),
        tokens_output=1,
    )


def execute_text_summarisation(prompt: str, **_: Any) -> ExecutionResult:
    checker = SummaryConstraintChecker()
    if checker.is_empty_or_whitespace(prompt):
        return ExecutionResult(
            success=False,
            error_code="empty_summary",
            error_message="summary is empty or whitespace",
            tokens_input=_approx_tokens(prompt),
        )
    return ExecutionResult(
        success=True,
        output=prompt,
        normalized_output=prompt.strip(),
        tokens_input=_approx_tokens(prompt),
        tokens_output=_approx_tokens(prompt),
    )


def execute_named_entity_recognition(prompt: str, **_: Any) -> ExecutionResult:
    validator = NamedEntityValidator()
    valid, entities, error = validator.validate_ner_output(prompt)
    if not valid:
        return ExecutionResult(
            success=False,
            error_code="invalid_ner",
            error_message=error,
            tokens_input=_approx_tokens(prompt),
        )
    return ExecutionResult(
        success=True,
        output=entities,
        normalized_output=entities,
        tokens_input=_approx_tokens(prompt),
        tokens_output=len(entities),
    )


def execute_code_debugging(prompt: str, **_: Any) -> ExecutionResult:
    checker = CodeSyntaxChecker()
    valid, errors = checker.validate_code_output(prompt)
    if not valid:
        return ExecutionResult(
            success=False,
            error_code="invalid_code",
            error_message="; ".join(errors),
            tokens_input=_approx_tokens(prompt),
        )
    return ExecutionResult(
        success=True,
        output=prompt,
        normalized_output=prompt,
        tokens_input=_approx_tokens(prompt),
        tokens_output=_approx_tokens(prompt),
    )


def execute_logical_reasoning(prompt: str, **_: Any) -> ExecutionResult:
    checker = LogicConsistencyChecker()
    valid, errors = checker.validate_logic_answer(prompt, prompt)
    if not valid:
        return ExecutionResult(
            success=False,
            error_code="invalid_logic",
            error_message="; ".join(errors),
            tokens_input=_approx_tokens(prompt),
        )
    return ExecutionResult(
        success=True,
        output=prompt,
        normalized_output=prompt,
        tokens_input=_approx_tokens(prompt),
        tokens_output=1,
    )


def execute_code_generation(prompt: str, **_: Any) -> ExecutionResult:
    validator = JSONValidator()
    valid, data, error = validator.parse(prompt)
    if not valid:
        return ExecutionResult(
            success=False,
            error_code="invalid_json",
            error_message=error,
            tokens_input=_approx_tokens(prompt),
        )
    output = data if isinstance(data, dict) else {"value": data}
    return ExecutionResult(
        success=True,
        output=output,
        normalized_output=output,
        tokens_input=_approx_tokens(prompt),
        tokens_output=_approx_tokens(prompt),
    )


EXECUTORS: Dict[str, Any] = {
    "mathematical_reasoning": execute_mathematical_reasoning,
    "factual_knowledge": execute_factual_knowledge,
    "sentiment_classification": execute_sentiment_classification,
    "text_summarisation": execute_text_summarisation,
    "named_entity_recognition": execute_named_entity_recognition,
    "code_debugging": execute_code_debugging,
    "logical_reasoning": execute_logical_reasoning,
    "code_generation": execute_code_generation,
}


def execute(capability_id: str, prompt: str, **kwargs: Any) -> ExecutionResult:
    """Dispatch to the executor registered for ``capability_id``."""
    executor = EXECUTORS.get(capability_id)
    if executor is None:
        return ExecutionResult(
            success=False,
            error_code="unknown_capability",
            error_message=f"no executor registered for capability_id={capability_id!r}",
            tokens_input=_approx_tokens(prompt),
        )
    return executor(prompt, **kwargs)


def list_executor_ids() -> List[str]:
    return sorted(EXECUTORS.keys())


# ---------------------------------------------------------------------------
# Public aliases
# ---------------------------------------------------------------------------
# These aliases allow capability definitions to reference executor functions
# by their capability_id (e.g. ``amd_track1.capabilities.executors.code_debugging``)
# in addition to the ``execute_*`` form.

mathematical_reasoning = execute_mathematical_reasoning
factual_knowledge = execute_factual_knowledge
sentiment_classification = execute_sentiment_classification
text_summarisation = execute_text_summarisation
named_entity_recognition = execute_named_entity_recognition
code_debugging = execute_code_debugging
logical_reasoning = execute_logical_reasoning
code_generation = execute_code_generation