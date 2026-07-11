"""Shared deterministic arithmetic prompt detection."""

from __future__ import annotations

import re
from typing import Optional


_OPERATOR_PATTERN = re.compile(r"(\*\*|[+\-*/%^])")
_DIGIT_PATTERN = re.compile(r"\d")
_PERCENT_OF_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*%\s+of\s+(\d+(?:\.\d+)?)",
    flags=re.IGNORECASE,
)
_DIRECT_CALCULATION_PATTERN = re.compile(
    r"^\s*(?:calculate|compute|evaluate|solve|what\s+is|what's|how\s+much\s+is)\s*:?\s*(.+?)\s*\??\s*$",
    flags=re.IGNORECASE,
)
_BLOCKED_CONTEXT_PATTERN = re.compile(
    r"\b(hash|sha|sha-\d+|http|endpoint|url|route|debug|diagnose|error|code|line|program|function)\b",
    flags=re.IGNORECASE,
)


def extract_arithmetic_expression(prompt: str) -> Optional[str]:
    """Extract a calculator-safe arithmetic expression from a prompt."""
    if not prompt:
        return None

    stripped = prompt.strip()
    direct_match = _DIRECT_CALCULATION_PATTERN.match(stripped)
    if not direct_match:
        return None

    expression_text = direct_match.group(1)
    if _BLOCKED_CONTEXT_PATTERN.search(expression_text):
        return None
    if re.search(r"\b(rounded|round|nearest|markup|discount|average speed|travels?|slows?|entire trip)\b", expression_text, re.IGNORECASE):
        return None

    percent_of = _PERCENT_OF_PATTERN.search(expression_text)
    if percent_of:
        return f"{percent_of.group(1)}% * {percent_of.group(2)}"

    allowed_chars = set("0123456789.+-*/%^() \t")
    candidates: list[str] = []
    start: Optional[int] = None

    for index, char in enumerate(expression_text):
        if char in allowed_chars:
            if start is None:
                start = index
        elif start is not None:
            candidates.append(expression_text[start:index].strip())
            start = None

    if start is not None:
        candidates.append(expression_text[start:].strip())

    candidates.sort(key=len, reverse=True)

    for candidate in candidates:
        expression = candidate.strip(" \t.:,;?!")
        if _DIGIT_PATTERN.search(expression) and _OPERATOR_PATTERN.search(expression):
            return expression

    return None


def has_arithmetic_expression(prompt: str) -> bool:
    """Return True when the prompt contains a deterministic arithmetic expression."""
    try:
        return extract_arithmetic_expression(prompt) is not None
    except Exception:
        return False
