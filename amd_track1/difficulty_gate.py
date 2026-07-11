"""
Difficulty Gate Module (v3 — Fireworks-only)

FIX: Local inference has been structurally removed from this module, not
just gated behind LOCAL_ALLOWED_CATEGORIES being empty. The previous version
kept a full local-eligibility code path that would activate the moment any
LOCAL_* env var was set. That is a real disqualification risk under the
rule that ALL inference must go through FIREWORKS_BASE_URL — local tokens
score zero regardless of intent. Rather than rely on config to keep that
path dormant, the path itself has been deleted.

This module now answers three questions, not four:
1. Is a deterministic solver available? (pure computation, zero tokens, safe)
2. Is Fireworks required? (always true if #1 fails)
3. Is post-answer validation required?

RoutingDecision.route can only ever be "deterministic" or "fireworks".
There is no "local" value anywhere in this file.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Literal, Optional, Tuple
from .arithmetic_detection import has_arithmetic_expression


# ---------------------------------------------------------------------------
# Routing decision
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RoutingDecision:
    """Immutable routing decision produced by the gate."""

    route: Literal["deterministic", "fireworks"]
    reason: str
    requires_validation: bool

    def to_dict(self) -> dict:
        return {
            "route": self.route,
            "reason": self.reason,
            "requires_validation": self.requires_validation,
        }


# ---------------------------------------------------------------------------
# Prompt feature extraction (unchanged — still useful for validation policy)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PromptFeatures:
    """Structural features extracted from a prompt."""

    prompt: str
    token_estimate: int
    source_text_length: int
    expected_output_length: int
    contains_code: bool
    constraint_count: int
    has_code_block: bool
    has_long_quoted_source: bool
    has_multi_step_requirement: bool
    has_strict_schema: bool
    has_multiple_outputs: bool
    has_requested_tests: bool


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for English text."""
    return max(1, len(text) // 4)


def extract_prompt_features(prompt: str) -> PromptFeatures:
    """Extract structural features from a prompt for validation decisions."""
    prompt_lower = prompt.lower().strip()
    token_estimate = estimate_tokens(prompt)
    source_text_length = len(prompt)

    has_code_block = "```" in prompt or "def " in prompt or "function " in prompt

    contains_code = has_code_block or any(
        kw in prompt_lower for kw in ("python", "javascript", "typescript", "java", "code", "script")
    )

    constraint_count = len(re.findall(r"\b(must|should|require|need)\b", prompt_lower))

    quoted_segments = re.findall(r'["\']([^"\']{50,})["\']', prompt)
    has_long_quoted_source = any(len(seg) > 200 for seg in quoted_segments)

    multi_step_patterns = [
        r"\b(multi[- ]?step|multiple\s+steps|then\s+.*then)\b",
        r"\b(first|second|third|finally)\b.*\b(and|then)\b",
        r"\bstep\s+\d+\b",
    ]
    has_multi_step_requirement = any(
        re.search(p, prompt_lower) for p in multi_step_patterns
    )

    has_strict_schema = bool(
        re.search(r"\b(json|yaml|xml|schema|format)\b", prompt_lower)
        and re.search(r"\b(output|return|respond)\b", prompt_lower)
    )

    has_multiple_outputs = bool(
        re.search(r"\b(list\s+all|find\s+all|enumerate|multiple\s+outputs)\b", prompt_lower)
    )

    has_requested_tests = bool(
        re.search(r"\b(test|tests|test\s+case|unit\s+test)\b", prompt_lower)
    )

    expected_output_length = 50
    if re.search(r"\b(one\s+sentence|single\s+word|yes\s+or\s+no|label)\b", prompt_lower):
        expected_output_length = 10
    elif re.search(r"\b(short|brief|concise)\b", prompt_lower):
        expected_output_length = 30
    elif re.search(r"\b(summary|summarize|explain|describe)\b", prompt_lower):
        expected_output_length = 200
    elif re.search(r"\b(comprehensive|detailed|full)\b", prompt_lower):
        expected_output_length = 500

    return PromptFeatures(
        prompt=prompt,
        token_estimate=token_estimate,
        source_text_length=source_text_length,
        expected_output_length=expected_output_length,
        contains_code=contains_code,
        constraint_count=constraint_count,
        has_code_block=has_code_block,
        has_long_quoted_source=has_long_quoted_source,
        has_multi_step_requirement=has_multi_step_requirement,
        has_strict_schema=has_strict_schema,
        has_multiple_outputs=has_multiple_outputs,
        has_requested_tests=has_requested_tests,
    )


# ---------------------------------------------------------------------------
# Deterministic solver detection (pure computation — zero tokens, always safe)
# ---------------------------------------------------------------------------

DETERMINISTIC_ARITHMETIC_PATTERNS = [
    re.compile(r"^\s*what\s+is\s+([\d\s+\-*/().]+)\s*\??\s*$", re.IGNORECASE),
    re.compile(r"^\s*calculate\s*:?\s*([\d\s+\-*/().]+)\s*$", re.IGNORECASE),
    re.compile(r"^\s*compute\s+([\d\s+\-*/().]+)\s*$", re.IGNORECASE),
    re.compile(r"^\s*([\d\s+\-*/().]+)\s*=\s*\??\s*$"),
    re.compile(r"^\s*solve\s+(\d+\s*[+\-*/]\s*\d+)\s*$", re.IGNORECASE),
    re.compile(r"^\s*evaluate\s+([\d\s+\-*/().]+)\s*$", re.IGNORECASE),
]

DETERMINISTIC_PERCENTAGE_PATTERNS = [
    re.compile(r"^\s*what\s+is\s+(\d+)\s*%\s*of\s+(\d+)\s*\??\s*$", re.IGNORECASE),
    re.compile(r"^\s*calculate\s+(\d+)\s*%\s*of\s+(\d+)\s*$", re.IGNORECASE),
]

DETERMINISTIC_TRANSFORMATION_PATTERNS = [
    re.compile(r"^\s*convert\s+(\d+)\s*(km|mi|m|ft|cm|in|kg|lb|g|oz)\s+to\s+(km|mi|m|ft|cm|in|kg|lb|g|oz)\s*\??\s*$", re.IGNORECASE),
]

DETERMINISTIC_EXTRACTION_PATTERNS = [
    re.compile(r"^\s*extract\s+(the\s+)?(email|phone|url|date)\s+from\s+['\"]([^'\"]{1,100})['\"]\s*\??\s*$", re.IGNORECASE),
]


def is_deterministic_solvable(category: str, prompt: str) -> Tuple[bool, str]:
    """
    Check if a deterministic tool can fully solve this task.
    This is regex/parsing only — no model, no tokens, no rule risk.
    """
    prompt_stripped = prompt.strip()

    if category == "mathematical_reasoning":
        if has_arithmetic_expression(prompt_stripped):
            return True, "Deterministic arithmetic"

        for pattern in DETERMINISTIC_TRANSFORMATION_PATTERNS:
            if pattern.match(prompt_stripped):
                return True, "Deterministic unit conversion"

    if category == "named_entity_recognition":
        for pattern in DETERMINISTIC_EXTRACTION_PATTERNS:
            if pattern.match(prompt_stripped):
                return True, "Deterministic exact-format extraction"

    return False, ""


# ---------------------------------------------------------------------------
# DifficultyAnalyzer (kept for validation-strictness signal only)
# ---------------------------------------------------------------------------

class DifficultyAnalyzer:
    """Analyzes task difficulty based on structural features."""

    def analyze(self, category: str, prompt: str) -> PromptFeatures:
        return extract_prompt_features(prompt)

    def is_complex(self, features: PromptFeatures) -> Tuple[bool, str]:
        reasons: List[str] = []

        if features.has_code_block:
            reasons.append("contains code block")
        if features.has_long_quoted_source:
            reasons.append("long quoted source text")
        if features.has_multi_step_requirement:
            reasons.append("multi-step requirement")
        if features.has_strict_schema:
            reasons.append("strict schema output required")
        if features.has_multiple_outputs:
            reasons.append("multiple outputs requested")
        if features.has_requested_tests:
            reasons.append("tests requested")
        if features.constraint_count > 2:
            reasons.append(f"multiple constraints ({features.constraint_count})")

        if reasons:
            return True, "; ".join(reasons)

        return False, ""


# ---------------------------------------------------------------------------
# ValidationPolicy (unchanged in behavior, local references removed)
# ---------------------------------------------------------------------------

class ValidationPolicy:
    """Determines whether post-answer validation is required."""

    ALWAYS_VALIDATE_CATEGORIES = frozenset({
        "code_generation",
        "code_debugging",
        "mathematical_reasoning",
        "named_entity_recognition",
    })

    CONDITIONAL_VALIDATE_CATEGORIES = frozenset({
        "sentiment_classification",
        "logical_reasoning",
    })

    def requires_validation(
        self,
        category: str,
        prompt: str,
        features: Optional[PromptFeatures] = None,
    ) -> Tuple[bool, str]:
        if category in self.ALWAYS_VALIDATE_CATEGORIES:
            return True, f"Category '{category}' always requires validation"

        if category in self.CONDITIONAL_VALIDATE_CATEGORIES:
            if features is None:
                features = extract_prompt_features(prompt)
            if features.has_strict_schema or features.constraint_count > 1:
                return True, "Structured output or multiple constraints require validation"
            return False, "Simple output, validation optional"

        if features is None:
            features = extract_prompt_features(prompt)
        if features.has_strict_schema:
            return True, "Strict schema requires validation"

        return False, "No validation required"


# ---------------------------------------------------------------------------
# RoutePolicy — Fireworks-only. No local branch exists in this class.
# ---------------------------------------------------------------------------

class RoutePolicy:
    """
    Main routing policy.

    Routing hierarchy:
    1. Deterministic solver available → deterministic (zero tokens, safe)
    2. Everything else → fireworks

    There is no local branch. This is not a config default — it is the only
    code path that exists in this class.
    """

    def __init__(
        self,
        validation: Optional[ValidationPolicy] = None,
        analyzer: Optional[DifficultyAnalyzer] = None,
    ):
        self._analyzer = analyzer or DifficultyAnalyzer()
        self._validation = validation or ValidationPolicy()

    def choose_route(
        self,
        category: str,
        prompt: str,
        deterministic_supported: bool = True,
    ) -> RoutingDecision:
        """
        Choose the routing decision for a task.

        Args:
            category: The task category
            prompt: The task prompt
            deterministic_supported: Whether deterministic tools are available

        Returns:
            RoutingDecision (route is always "deterministic" or "fireworks")
        """
        if deterministic_supported:
            det_ok, det_reason = is_deterministic_solvable(category, prompt)
            if det_ok:
                return RoutingDecision(
                    route="deterministic",
                    reason=det_reason,
                    requires_validation=False,
                )

        features = extract_prompt_features(prompt)
        val_required, val_reason = self._validation.requires_validation(
            category, prompt, features
        )

        return RoutingDecision(
            route="fireworks",
            reason="Routed to Fireworks (no deterministic solver available)",
            requires_validation=val_required,
        )


# ---------------------------------------------------------------------------
# Convenience functions (backward-compatible API, local params removed)
# ---------------------------------------------------------------------------

_default_policy: Optional[RoutePolicy] = None


def _get_default_policy() -> RoutePolicy:
    global _default_policy
    if _default_policy is None:
        _default_policy = RoutePolicy()
    return _default_policy


def assess_difficulty(category: str, prompt: str) -> Tuple[bool, str]:
    """Legacy compatibility: assess whether a task is 'easy' (= deterministic)."""
    decision = _get_default_policy().choose_route(category, prompt)
    is_easy = decision.route == "deterministic"
    return is_easy, decision.reason


def should_skip_subagent(category: str, prompt: str, validation_passed: bool) -> Tuple[bool, str]:
    """Legacy compatibility: determine if subagent should be skipped."""
    decision = _get_default_policy().choose_route(category, prompt)
    if decision.route == "deterministic":
        return True, "Deterministic solve"
    return False, decision.reason


def choose_route(
    category: str,
    prompt: str,
    deterministic_supported: bool = True,
) -> RoutingDecision:
    """Main routing function. Fireworks-only — no local_eligible or
    model_available parameters, because there is nothing local left to
    check availability of."""
    policy = _get_default_policy()
    return policy.choose_route(
        category=category,
        prompt=prompt,
        deterministic_supported=deterministic_supported,
    )


def get_category_easiness_score(category: str, prompt: str) -> float:
    """Return a score from 0.0 (very hard) to 1.0 (very easy)."""
    decision = _get_default_policy().choose_route(category, prompt)
    if decision.route == "deterministic":
        return 1.0
    return 0.3


# ---------------------------------------------------------------------------
# DifficultyGate class
# ---------------------------------------------------------------------------

class DifficultyGate:
    """Typed gate component with immutable configuration. Fireworks-only."""

    def __init__(
        self,
        validation: Optional[ValidationPolicy] = None,
        analyzer: Optional[DifficultyAnalyzer] = None,
        policy_version: str = "3.0.0-fireworks-only",
    ):
        self._analyzer = analyzer or DifficultyAnalyzer()
        self._validation = validation or ValidationPolicy()
        self._policy = RoutePolicy(
            validation=self._validation,
            analyzer=self._analyzer,
        )
        self._policy_version = policy_version

    @property
    def policy_version(self) -> str:
        return self._policy_version

    def assess_difficulty(self, category: str, prompt: str) -> Tuple[bool, str]:
        return assess_difficulty(category, prompt)

    def should_skip_subagent(
        self, category: str, prompt: str, validation_passed: bool
    ) -> Tuple[bool, str]:
        return should_skip_subagent(category, prompt, validation_passed)

    def choose_route(
        self,
        category: str,
        prompt: str,
        deterministic_supported: bool = True,
    ) -> RoutingDecision:
        return choose_route(category, prompt, deterministic_supported)

    def get_category_easiness_score(self, category: str, prompt: str) -> float:
        return get_category_easiness_score(category, prompt)


# Singleton instance
_gate_instance: Optional[DifficultyGate] = None


def get_difficulty_gate() -> DifficultyGate:
    """Get the difficulty gate instance."""
    global _gate_instance
    if _gate_instance is None:
        _gate_instance = DifficultyGate()
    return _gate_instance
