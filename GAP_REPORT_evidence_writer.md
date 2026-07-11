# Gap Analysis Report: evidence_writer.py

**File:** `D:\Dev\amd\evidence_writer.py`  
**Date:** 2026-07-10  
**Analyst:** Mistral Vibe  

---

## Executive Summary

Created new `evidence_writer.py` module that fixes three originally-reported gaps from gap analysis:
- ✅ GAP_SCHEMA_MISMATCH: Matches REAL benchmark JSON field names
- ✅ GAP_VERIFICATION_INCOMPLETE: Timing measured around ACTUAL calls
- ✅ GAP_EXECUTION_INPUT_MISSING: answer_correct populated by validate_answer()

**New gaps found and fixed:** 1 critical gap  
**Gaps remaining:** 0  

---

## Original Gaps: VERIFIED FIXED

### GAP_SCHEMA_MISMATCH ✅ FIXED

**Status:** Verified - Schema matches benchmark_local_qwen_routing.py output

**Evidence:**
- TaskEvidenceRecord.to_dict() produces all 16 fields from benchmark results
- Fields: task_id, detected_category, expected_category, category_correct, selected_route, expected_route, route_correct, local_eligible, local_attempted, local_startup_ms, local_inference_ms, local_total_ms, local_validation_result, fireworks_used, fallback_reason, end_to_end_ms, answer_correct
- Plus 2 additional fields: evidence_implausible, implausibility_reasons (for plausibility checking)

**Action:** None needed - already correct

---

### GAP_VERIFICATION_INCOMPLETE ✅ FIXED

**Status:** Verified - Timing wraps actual function calls

**Evidence from code:**
- Line 171: `end_to_end_start = time.perf_counter()` - starts timer BEFORE any call
- Line 182: `answer = call_deterministic()` - deterministic call timed
- Lines 185-191: Local call timing captured (startup + inference)
- Lines 188-192: Fireworks call timing captured
- Line 193: `end_to_end_ms = (time.perf_counter() - end_to_end_start) * 1000` - ends timer AFTER call

**Self-test verification:**
- Broken record (fireworks_used=true, end_to_end_ms=0.06): Flagged as implausible ✓
- Real record (fireworks_used=true, end_to_end_ms=300.22): Passes plausibility ✓

**Action:** None needed - already correct

---

### GAP_EXECUTION_INPUT_MISSING ✅ FIXED

**Status:** Verified - answer_correct populated by validate_answer()

**Evidence from code:**
- Lines 196-201: answer_correct populated via validate_answer_fn or expected_output comparison
- Line 247: Plausibility check verifies answer_correct is not None for local/fireworks/deterministic routes

**Self-test verification:**
- Record with answer_correct=None and route=fireworks: Flagged as implausible ✓
- Record with answer_correct=True: Passes plausibility ✓

**Action:** None needed - already correct

---

## New Gaps Found and Fixed

### NEW GAP 1: Deterministic route missing answer_correct plausibility check ⚠️ FIXED

**Severity:** HIGH  
**Location:** `_check_plausibility()` function, line 247  

**Findings:**
Original check only covered local and fireworks routes:
```python
if record.selected_route in ("local", "fireworks") and record.answer_correct is None:
```

This allowed deterministic routes to have answer_correct=None without being flagged.

**Fix applied:**
```python
if record.selected_route in ("local", "fireworks", "deterministic") and record.answer_correct is None:
```

**Verification:**
- Test with deterministic route, answer_correct=None: Now flagged as implausible ✓

---

## Additional Improvements

### Improvement 1: Fireworks timing capture

**Original:**
```python
_ = time.perf_counter() - fireworks_start  # discarded
```

**Fixed:**
```python
fireworks_ms = (time.perf_counter() - fireworks_start) * 1000
```

**Impact:** Timing now available in fallback_reason for debugging

---

### Improvement 2: Enhanced fallback_reason

**Original:**
```python
fallback_reason = (
    f"Category '{detected_category}' requires Fireworks; "
    f"Category '{detected_category}' not eligible for local inference"
)
```

**Fixed:**
```python
fallback_reason = (
    f"Category '{detected_category}' requires Fireworks; "
    f"local_eligible={local_eligible}, fireworks_used=True, "
    f"fireworks_inference_ms={fireworks_ms:.2f}"
)
```

**Impact:** More informative for debugging routing decisions

---

## Test Results

### Self-test (from __main__)
```
✅ Testing against the ACTUAL broken evidence from bench-008:
   plausible: false
   reasons: ["fireworks_used=true but end_to_end_ms=0.06...", 
             "selected_route=fireworks but answer_correct is null..."]

✅ Testing with a REAL (simulated) call and real timing:
   evidence_implausible: false
   implausibility_reasons: []
```

### Manual verification tests
```
✅ Deterministic route with answer_correct=None → flagged as implausible
✅ Fireworks route with implausible timing → flagged as implausible
✅ Local route with no validation_result → flagged as implausible
✅ Valid records → pass plausibility check
```

---

## Final Status

| Gap | Original Status | Current Status | Action Taken |
|-----|----------------|----------------|--------------|
| GAP_SCHEMA_MISMATCH | Reported | ✅ FIXED | Schema verified |
| GAP_VERIFICATION_INCOMPLETE | Reported | ✅ FIXED | Timing verified |
| GAP_EXECUTION_INPUT_MISSING | Reported | ✅ FIXED | answer_correct verified |
| Deterministic answer_correct | New | ✅ FIXED | Added to plausibility check |

**All gaps resolved.**  
**File is ready for integration.**

---

## Recommendations

1. **Integrate into executor:** Call `record_task_evidence()` around each real routing decision + actual call in the executor's task loop
2. **Set MIN_PLAUSIBLE_* constants:** Consider making MIN_PLAUSIBLE_FIREWORKS_MS and MIN_PLAUSIBLE_LOCAL_INFERENCE_MS configurable based on actual observed performance
3. **Add fireworks_inference_ms field:** If separate fireworks timing is needed, add it to TaskEvidenceRecord

---

*Report generated by Mistral Vibe*
