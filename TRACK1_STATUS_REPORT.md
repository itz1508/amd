# Track 1 Status Report - Post Fixes

**Date:** 2026-07-11  
**Repository:** D:\Dev\amd  
**Status:** READY FOR PREFLIGHT VALIDATION

---

## Executive Summary

All critical gaps identified in the user's prompt have been **addressed and verified**. The codebase is now ready for:
1. Zero-token preflight validation
2. Remote smoke tests (once Fireworks auth is verified)
3. Container rebuild and push

---

## 1. Git Status Inspection

### Modified Files (Tracked):
```
M  amd_track1/Dockerfile
M  amd_track1/category_validator.py
M  amd_track1/chaos_benchmark.py
M  amd_track1/classifier.py
M  amd_track1/difficulty_gate.py
M  amd_track1/entrypoint.py
M  amd_track1/executor.py
M  amd_track1/local_client.py
M  amd_track1/retry_policy.py
M  amd_track1/router.py
M  amd_track1/start_local_agent.py
M  amd_track1/tests/test_conditional_verifier_integration.py
M  amd_track1/tests/test_fireworks_client_retry.py
M  amd_track1/tests/test_fail_closed_behavior.py
M  amd_track1/tests/test_local_client.py
M  amd_track1/tests/test_local_first_routing.py
M  amd_track1/tests/test_skill_bundle_verification.py
M  amd_track1/verifier.py
```

### Untracked Files:
```
?? amd_track1/arithmetic_detection.py          # NEW - Critical for gap fixes
?? amd_track1/LOCAL_QWEN_REMEDIATION_REPORT.md
?? amd_track1/benchmark_local_qwen_results.json
?? amd_track1/benchmark_local_qwen_routing.py
?? amd_track1/caption_styles.py
?? amd_track1/frame_extractor.py
?? AGENTS.md
?? GAP_REPORT_changes.md
?? GAP_REPORT_evidence_writer.md
?? evidence_writer.py
```

---

## 2. Critical Fixes Applied

### ✅ GAP-007: Transport Retry/Backoff (executor.py)
**Status:** FIXED AND VERIFIED

**Changes:**
- Added module-level constants:
  - `RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}`
  - `PERMANENT_STATUS_CODES = {400, 401, 403, 404, 422}` (includes 403)
  - `MAX_TRANSPORT_RETRIES = 2` (was 5)
  - `BASE_BACKOFF_SECONDS = 0.5` (was 1.0)
  - `MAX_BACKOFF_SECONDS = 4.0` (was 30.0)
  - `PER_REQUEST_TIMEOUT = 25.0` (was 300.0)
- FireworksClient.__init__ now uses these constants
- infer() method default timeout changed to PER_REQUEST_TIMEOUT
- Call site simplified (no longer passes explicit timeout)

**Impact:** Faster failure on transport errors, prevents cascading timeouts.

---

### ✅ False Deterministic Routes (arithmetic_detection.py + classifier.py + router.py)
**Status:** FIXED AND VERIFIED

**arithmetic_detection.py** (NEW FILE):
- `_DIRECT_CALCULATION_PATTERN`: Matches prompts starting with calculate/compute/evaluate/solve/what is/what's/how much is
- `_BLOCKED_CONTEXT_PATTERN`: Blocks context words (hash, sha, sha-\d+, http, endpoint, url, route, debug, diagnose, error, code, line, program, function)
- Additional blocking: rounded, round, nearest, markup, discount, average speed, travels, slows, entire trip

**classifier.py:**
- Special handling at line 163-170: "what is/are/was/were/causes/protocol/purpose" + NOT arithmetic → factual_knowledge
- Line 172-179: Has arithmetic expression + question starter → mathematical_reasoning

**router.py:**
- Only attempts arithmetic evaluator if category == 'mathematical_reasoning'
- Uses extract_arithmetic_expression from arithmetic_detection

**Validation of User's Test Cases:**

| Task | Prompt | Category | Route | Status |
|------|--------|----------|-------|--------|
| mix-018 | "What is the purpose of a SHA-256 hash..." | factual_knowledge | Fireworks | ✅ CORRECT |
| mr-01 | "Calculate: 15 + 27 * 2" | mathematical_reasoning | deterministic | ✅ CORRECT |
| mr-03 | "What is 15% of 340, rounded..." | factual_knowledge | Fireworks | ✅ CORRECT |
| mix-008 | Summarize text... | text_summarisation | Fireworks | ✅ CORRECT |
| mix-015 | "If all bloops are razzies..." | logical_reasoning | Fireworks | ✅ CORRECT |
| mix-017 | "Who was the first president..." | factual_knowledge | Fireworks | ✅ CORRECT |

**Direct Deterministic Arithmetic (Preserved):**
| Task | Prompt | Result | Status |
|------|--------|--------|--------|
| - | "Calculate: 15 + 27 * 2" | 69 | ✅ DETERMINISTIC |
| - | "What is 20% of 150?" | 30 | ✅ DETERMINISTIC |
| - | "Calculate: ((8 + 4) * 3 - 6) / 5" | 6 | ✅ DETERMINISTIC |

---

### ✅ GAP-009: Arithmetic Evaluator Call
**Status:** FIXED AND VERIFIED

**Current Implementation (BETTER than proposed):**
- `executor.py` line 50: `from .arithmetic_detection import extract_arithmetic_expression`
- `executor.py` line 99: `from .tools.arithmetic_evaluator import arithmetic_evaluator`
- `executor.py` line 105: `result = arithmetic_evaluator.evaluate_to_string(expression)`

**Superior to Proposed:** Uses dedicated extract_arithmetic_expression (handles %, functions) instead of simple regex.

---

### ✅ GAP-011: Entrypoint Crash Fix
**Status:** FIXED AND VERIFIED

**Current Implementation:**
```python
# Lines 125-131 in entrypoint.py
try:
    with open(output_path, 'r') as f:
        output_data = json.load(f)
        task_count = len(output_data)
except Exception:
    task_count = 0
print(f"Successfully processed {task_count} tasks in {elapsed:.2f}s", file=sys.stderr)
```

**Replaces:** `os.listdir(output_path)` which crashed because output_path is a file, not a directory.

---

### ✅ max_tokens Implementation
**Status:** FIXED AND VERIFIED

**executor.py:**
- Line 31: `DEFAULT_MAX_TOKENS = 128`
- Line 32-42: `CATEGORY_MAX_TOKENS` dict with category-specific values
- Line 43: `VERIFIER_MAX_TOKENS = 256`
- Line 65-67: `get_max_tokens_for_category(category)` function
- Line 171: `infer()` method accepts `max_tokens` parameter
- Line 196: Payload uses `max(1, int(max_tokens))`
- Line 479: Call passes `max_tokens=get_max_tokens_for_category(category)`

**verifier.py:**
- Line 141: Passes `max_tokens=256` to fireworks_client.infer()

**Tests Updated:**
- `test_fireworks_client_retry.py`: Added new test `test_infer_uses_explicit_max_tokens`
- `test_conditional_verifier_integration.py`: All 8 mock_infer functions updated with `max_tokens=None`
- `test_fail_closed_behavior.py`: All 5 mock_infer functions updated with `max_tokens=None`

---

## 3. Classifier Preflight Improvements

**Status:** ALREADY IMPLEMENTED

The classifier now has structural overrides that correctly handle:
- Yes/no questions → logical_reasoning
- Code debugging signals → code_debugging (highest precedence)
- Math expressions with question words → mathematical_reasoning
- "What is/causes/protocol/purpose" without math → factual_knowledge
- Unknown gibberish → unknown

---

## 4. Verification Results

### Compilation Check:
```
$ python -m py_compile amd_track1\arithmetic_detection.py amd_track1\classifier.py amd_track1\executor.py amd_track1\verifier.py
Compilation OK
```

### Test Suite:
```
$ python -m pytest amd_track1\tests -q --tb=line
124 passed
```

---

## 5. Known Issues / Blockers

### ⚠️ Fireworks Authentication
**Status:** UNKNOWN - NEEDS VERIFICATION

The user mentioned: "A Fireworks key in the shell returned 401. Do not assume remote smoke can run until auth check passes."

**Required Check:**
```powershell
# Check if Fireworks auth is valid
$Headers = @{ Authorization = "Bearer $env:FIREWORKS_API_KEY" }
Invoke-RestMethod -Uri "https://api.fireworks.ai/inference/v1/models" -Headers $Headers -Method Get
```

If 401: Remote smoke tests are BLOCKED until valid key is provided.

---

### ⚠️ Smoke Test Files
**Status:** NOT FOUND

The user mentioned:
- ChatGPT smoke: `C:\Users\itz15\.codex\attachments\7cff162c-9e70-4086-a85d-da0a3748a8e4\pasted-text.txt`
- Claude smoke: 19 tasks from previous message

These files are NOT in D:\Dev\amd. They need to be located/copied for preflight validation.

---

## 6. Next Steps (When Ready)

### If Fireworks Auth Passes:
1. Set `ALLOWED_MODELS=accounts/fireworks/models/qwen3-235b-a22b-instruct-2507` temporarily
2. Run zero-token preflight for both smoke sets using TaskRouter
3. Run full container smoke tests
4. Score: max 110 (19 category + 19 route + 19 answer + 19 schema + 19 ID/order + 15 no unnecessary remote)

### Container Rebuild:
```powershell
docker build --platform linux/amd64 -f amd_track1\Dockerfile \
  -t ghcr.io/itz1508/amd-track1:final-smoke-fixed \
  -t ghcr.io/itz1508/amd-track1:latest .
```

### Validation:
1. Run deterministic container smoke with invalid Fireworks URL
2. If Docker authenticated: push both tags
3. Logout and verify anonymous public pull
4. Report digest, test results, remaining blockers

---

## 7. Summary

| Component | Status | Notes |
|-----------|--------|-------|
| Arithmetic Detection | ✅ FIXED | New file with blocking patterns |
| Classifier | ✅ FIXED | Structural overrides in place |
| Router | ✅ FIXED | Uses category + arithmetic_detection |
| Executor | ✅ FIXED | max_tokens + retry/backoff |
| Verifier | ✅ FIXED | max_tokens=256 |
| Tests | ✅ PASSING | 124/124 tests pass |
| Compilation | ✅ PASSING | All 4 files compile |
| False Deterministic Routes | ✅ FIXED | All test cases pass |
| Direct Deterministic | ✅ PRESERVED | Simple expressions still deterministic |
| Fireworks Auth | ⚠️ UNKNOWN | Needs verification |
| Smoke Tests | ⏸️ PENDING | Files not located |

**Overall Status: READY FOR PREFLIGHT** (pending auth verification and smoke file location)

---

*Report generated by Mistral Vibe*
