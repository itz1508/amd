"""
evidence_writer.py

Fixes the three gaps found in the gap analysis:
  - GAP_SCHEMA_MISMATCH: matches the REAL field names seen in the actual
    benchmark JSON (local_startup_ms, local_inference_ms, local_total_ms,
    end_to_end_ms, detected_category, answer_correct) — not the different
    names chaos_benchmark.py's TaskEvidence dataclass expects.
  - GAP_VERIFICATION_INCOMPLETE: timing is measured around the ACTUAL
    call, not set to 0 while a flag claims the call happened.
  - GAP_EXECUTION_INPUT_MISSING: answer_correct is actually populated by
    calling validate_answer(), never left as null.

Drop this into the executor's task loop — call record_task_evidence()
around each real routing decision + actual call, not after the fact.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

# Minimum plausible durations — used to catch the exact bug we found:
# fireworks_used=true with end_to_end_ms < 50 is physically impossible
# for a real network round trip. Same idea for local model inference.
MIN_PLAUSIBLE_FIREWORKS_MS = 50.0
MIN_PLAUSIBLE_LOCAL_INFERENCE_MS = 5.0


@dataclass
class TaskEvidenceRecord:
    """
    Matches the REAL schema found in the actual benchmark JSON —
    not chaos_benchmark.py's TaskEvidence dataclass, which uses
    different field names entirely (that mismatch was GAP_SCHEMA_MISMATCH).
    """
    task_id: str
    detected_category: str
    expected_category: str
    selected_route: str  # "deterministic" | "local" | "fireworks"
    expected_route: str
    local_eligible: bool
    local_attempted: bool
    local_startup_ms: float
    local_inference_ms: float
    local_total_ms: float
    local_validation_result: Optional[dict]
    fireworks_used: bool
    fallback_reason: Optional[str]
    end_to_end_ms: float
    answer_correct: Optional[bool]
    evidence_implausible: bool = False
    implausibility_reasons: list = field(default_factory=list)

    @property
    def category_correct(self) -> bool:
        return self.detected_category == self.expected_category

    @property
    def route_correct(self) -> bool:
        return self.selected_route == self.expected_route

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "detected_category": self.detected_category,
            "expected_category": self.expected_category,
            "category_correct": self.category_correct,
            "selected_route": self.selected_route,
            "expected_route": self.expected_route,
            "route_correct": self.route_correct,
            "local_eligible": self.local_eligible,
            "local_attempted": self.local_attempted,
            "local_startup_ms": self.local_startup_ms,
            "local_inference_ms": self.local_inference_ms,
            "local_total_ms": self.local_total_ms,
            "local_validation_result": self.local_validation_result,
            "fireworks_used": self.fireworks_used,
            "fallback_reason": self.fallback_reason,
            "end_to_end_ms": self.end_to_end_ms,
            "answer_correct": self.answer_correct,
            "evidence_implausible": self.evidence_implausible,
            "implausibility_reasons": self.implausibility_reasons,
        }


def _check_plausibility(record: TaskEvidenceRecord) -> tuple[bool, list[str]]:
    """
    The actual fix for GAP_VERIFICATION_INCOMPLETE: catch physically
    impossible timing BEFORE it gets written as valid evidence, instead
    of silently accepting fireworks_used=true with end_to_end_ms=0.05.
    """
    reasons = []

    if record.fireworks_used and record.end_to_end_ms < MIN_PLAUSIBLE_FIREWORKS_MS:
        reasons.append(
            f"fireworks_used=true but end_to_end_ms={record.end_to_end_ms} "
            f"is below the minimum plausible network round-trip "
            f"({MIN_PLAUSIBLE_FIREWORKS_MS}ms) — the call likely never happened."
        )

    if record.local_attempted and record.local_inference_ms < MIN_PLAUSIBLE_LOCAL_INFERENCE_MS:
        reasons.append(
            f"local_attempted=true but local_inference_ms={record.local_inference_ms} "
            f"is below the minimum plausible local inference time "
            f"({MIN_PLAUSIBLE_LOCAL_INFERENCE_MS}ms) — inference likely never ran."
        )

    if record.local_attempted and record.local_validation_result is None:
        reasons.append(
            "local_attempted=true but local_validation_result is null — "
            "no proof the local response was ever checked."
        )

    if record.selected_route in ("local", "fireworks", "deterministic") and record.answer_correct is None:
        reasons.append(
            f"selected_route={record.selected_route} but answer_correct is null — "
            "validate_answer() was likely never called."
        )

    return len(reasons) == 0, reasons


def record_task_evidence(
    task_id: str,
    detected_category: str,
    expected_category: str,
    selected_route: str,
    expected_route: str,
    local_eligible: bool,
    task_prompt: str,
    expected_output: Optional[str],
    call_deterministic: Optional[Callable[[], str]] = None,
    call_local: Optional[Callable[[], str]] = None,
    call_fireworks: Optional[Callable[[], str]] = None,
    validate_answer_fn: Optional[Callable[[dict, Optional[str]], tuple]] = None,
) -> TaskEvidenceRecord:
    """
    Wraps REAL timing around the REAL call for whichever route was
    selected, then validates the actual answer. This is the fix: timing
    starts/stops around the actual function call, not left at 0 while a
    flag says the call happened.

    Pass in the actual callables for each route (deterministic solver,
    local Qwen call, Fireworks call) — whichever one matches
    `selected_route` actually gets invoked and timed for real.
    """
    end_to_end_start = time.perf_counter()

    local_attempted = False
    local_startup_ms = 0.0
    local_inference_ms = 0.0
    local_total_ms = 0.0
    local_validation_result = None
    fireworks_used = False
    fallback_reason = None
    answer = None

    if selected_route == "deterministic" and call_deterministic:
        answer = call_deterministic()

    elif selected_route == "local" and call_local:
        local_attempted = True
        startup_start = time.perf_counter()
        # In a real implementation, startup (model already loaded vs cold
        # start) would be measured separately from inference. Here we
        # measure the full call and attribute it to inference, since a
        # warm server has near-zero startup — adjust if cold-starting.
        local_startup_ms = 0.0
        inference_start = time.perf_counter()
        answer = call_local()
        local_inference_ms = (time.perf_counter() - inference_start) * 1000
        local_total_ms = local_startup_ms + local_inference_ms

        local_validation_result = {
            "non_empty": bool(answer and answer.strip()),
            "raw_answer": answer,
        }

    elif selected_route == "fireworks" and call_fireworks:
        fireworks_used = True
        fireworks_start = time.perf_counter()
        answer = call_fireworks()
        fireworks_ms = (time.perf_counter() - fireworks_start) * 1000
        fallback_reason = (
            f"Category '{detected_category}' requires Fireworks; "
            f"local_eligible={local_eligible}, fireworks_used=True, "
            f"fireworks_inference_ms={fireworks_ms:.2f}"
        )

    end_to_end_ms = (time.perf_counter() - end_to_end_start) * 1000

    answer_correct = None
    if validate_answer_fn is not None and answer is not None:
        task_dict = {"prompt": task_prompt, "category": detected_category}
        is_valid, _errors = validate_answer_fn(task_dict, answer)
        answer_correct = is_valid
    elif expected_output is not None and answer is not None:
        answer_correct = (answer.strip() == expected_output.strip())

    record = TaskEvidenceRecord(
        task_id=task_id,
        detected_category=detected_category,
        expected_category=expected_category,
        selected_route=selected_route,
        expected_route=expected_route,
        local_eligible=local_eligible,
        local_attempted=local_attempted,
        local_startup_ms=round(local_startup_ms, 2),
        local_inference_ms=round(local_inference_ms, 2),
        local_total_ms=round(local_total_ms, 2),
        local_validation_result=local_validation_result,
        fireworks_used=fireworks_used,
        fallback_reason=fallback_reason,
        end_to_end_ms=round(end_to_end_ms, 2),
        answer_correct=answer_correct,
    )

    plausible, reasons = _check_plausibility(record)
    record.evidence_implausible = not plausible
    record.implausibility_reasons = reasons

    return record


if __name__ == "__main__":
    import json

    # Self-test: simulate what the ORIGINAL buggy evidence looked like
    # (flags set, no real call, zero timing) and confirm plausibility
    # checking now catches it.
    fake_broken_record = TaskEvidenceRecord(
        task_id="bench-008",
        detected_category="code_debugging",
        expected_category="code_debugging",
        selected_route="fireworks",
        expected_route="fireworks",
        local_eligible=False,
        local_attempted=False,
        local_startup_ms=0,
        local_inference_ms=0,
        local_total_ms=0,
        local_validation_result=None,
        fireworks_used=True,
        fallback_reason="Category 'code_debugging' requires Fireworks",
        end_to_end_ms=0.06,  # the actual implausible value from the real report
        answer_correct=None,
    )

    plausible, reasons = _check_plausibility(fake_broken_record)
    print("Testing against the ACTUAL broken evidence from bench-008:")
    print(json.dumps({"plausible": plausible, "reasons": reasons}, indent=2))

    # Now simulate a REAL call with realistic timing to confirm it passes
    def fake_real_fireworks_call():
        time.sleep(0.3)  # simulate a real ~300ms network round trip
        return "The bug is on line 3: missing self parameter"

    def fake_validate(task_dict, answer):
        return True, []

    real_record = record_task_evidence(
        task_id="bench-008-fixed",
        detected_category="code_debugging",
        expected_category="code_debugging",
        selected_route="fireworks",
        expected_route="fireworks",
        local_eligible=False,
        task_prompt="Fix the bug on line 3",
        expected_output=None,
        call_fireworks=fake_real_fireworks_call,
        validate_answer_fn=fake_validate,
    )

    print("\nTesting with a REAL (simulated) call and real timing:")
    print(json.dumps(real_record.to_dict(), indent=2))
