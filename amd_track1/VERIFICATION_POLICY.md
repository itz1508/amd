# AMD Track 1 Verification Policy

## Fail-Closed Behavior Rules

### Core Principle
**Never return an answer known to be invalid.** The pipeline must fail closed, preserving valid answers and blocking invalid ones.

---

### Decision Matrix

| Scenario | Solver Answer | Local Validation | Verifier Called | Verifier Result | Final Behavior |
|----------|---------------|------------------|-----------------|-----------------|----------------|
| D1 | Valid | Pass | No | N/A | Return solver answer |
| D2 | Valid | Pass | Yes | Valid JSON, accepted | Return verifier answer |
| D3 | Valid | Pass | Yes | Valid JSON, revised | Return verifier answer |
| D4 | Valid | Pass | Yes | Invalid JSON | Return solver answer (preserve valid) |
| D5 | Valid | Pass | Yes | Valid JSON but fails local validation | Return solver answer |
| D6 | Valid | Pass | Yes | Transport error (transient) | Return solver answer |
| D7 | Valid | Pass | Yes | Transport error (permanent) | Return solver answer |
| I1 | Invalid | Fail | Yes | Valid JSON, accepted | Return verifier answer if valid |
| I2 | Invalid | Fail | Yes | Valid JSON, revised | Return verifier answer if valid |
| I3 | Invalid | Fail | Yes | Invalid JSON | **BLOCK** - No valid answer, fail task |
| I4 | Invalid | Fail | Yes | Valid JSON but fails local validation | **BLOCK** - No valid answer, fail task |
| I5 | Invalid | Fail | No | N/A | **BLOCK** - No valid answer, fail task |
| E1 | Empty | N/A | No | N/A | **BLOCK** - Fail task |

---

### Specific Rules

#### 1. Locally Invalid Solver Answer + Verifier Failure
**Rule:** BLOCK - Task fails, no answer returned.

**Rationale:** If the solver produces an answer that fails local validation, and the verifier also fails (invalid JSON, transport error, or invalid correction), there is no valid answer to return. The task must fail rather than return known-invalid output.

**Implementation:**
```python
if not local_validation_passed and not verifier_provided_valid_answer:
    return ExecutionResult(success=False, answer=None, ...)
```

#### 2. Locally Valid High-Risk Solver Answer + Verifier Failure
**Rule:** PRESERVE solver answer, record `unverified` status.

**Rationale:** A locally valid answer from a high-risk category that cannot be verified is still better than no answer. However, this must be explicitly recorded as unverified for audit purposes.

**Implementation:**
```python
if local_validation_passed and category in HIGH_RISK_CATEGORIES:
    if verifier_failed:
        # Preserve solver answer but mark as unverified
        result.unverified = True
        result.verifier_status = "failed"
        return solver_answer
```

#### 3. Verifier Correction Failing Local Validation
**Rule:** PRESERVE solver answer if it was valid.

**Rationale:** If the verifier returns a correction but that correction fails local validation, the solver's valid answer must not be replaced. The verifier's correction is rejected, and the original valid answer stands.

**Implementation:**
```python
if verifier_result.get("validated"):
    if local_validate(verifier_result["final_answer"]):
        return verifier_result["final_answer"]
    else:
        # Verifier correction failed validation - keep solver answer
        return solver_answer
```

#### 4. Maximum One Verifier Call
**Rule:** Verifier must be called at most once per task.

**Rationale:** Prevents infinite correction loops and uncontrolled token usage.

**Implementation:**
- Track verifier invocation in `ExecutionResult`
- Reject any second verifier call with `RuntimeError`

#### 5. Solver and Verifier Model Separation
**Rule:** When both SOLVER_MODEL and VERIFIER_MODEL are explicitly set and different, they must be used. If only ALLOWED_MODELS is set, solver uses first model, verifier uses last model (if different).

**Runtime Check:**
```python
if solver_model == verifier_model:
    # Log warning but allow (degraded mode)
    warnings.warn("Solver and verifier use same model - degraded mode")
```

---

### Verifier Invocation Policy

**Verifier MUST be called when:**
1. Category is in HIGH_RISK_CATEGORIES (`code_generation`, `code_debugging`, `logical_reasoning`, `named_entity_recognition`)
2. Local validation fails for the solver answer

**Verifier MUST NOT be called when:**
1. Deterministic tool fully solves the task (zero model calls)
2. Solver answer is valid AND category is low-risk

**Verifier Call Limit:** Exactly one call per task maximum.

---

### Output Contract Enforcement

**Always:**
- Output contains exactly `task_id` and `answer` fields
- `answer` is always a string
- No duplicate `task_id` values
- All input `task_id` values appear exactly once in output (or task fails)
- Output is written atomically
- Output is re-read and schema-validated before success is claimed

**Failure Modes:**
- If output validation fails: fail the entire pipeline, do not return partial results
- If atomic write fails: fail the entire pipeline
- If re-read validation fails: fail the entire pipeline

---

### Error Handling

**Transient Errors (Retry):**
- HTTP 429, 500, 502, 503, 504
- Connection errors
- Timeout errors
- These trigger transport-level retries (handled by FireworksClient)
- Do NOT consume the task-level retry budget

**Permanent Errors (No Retry):**
- HTTP 400, 401, 404, 422
- Invalid model ID
- Authentication errors
- These do NOT trigger retries

**Model Selection Retry:**
- On permanent error, try next model from ALLOWED_MODELS
- Maximum attempts per task: 2 (configurable)

---

### Token Accounting

**Every Fireworks call MUST record:**
- `model_id`
- `role` (solver or verifier)
- `task_id`
- `category`
- `prompt_tokens`
- `completion_tokens`
- `total_tokens`
- `latency`
- `retry_count`

**Zero Token Tasks:**
- Deterministic tool solutions: `solver_tokens = 0`, `verifier_tokens = 0`
- Must be provably zero (no FireworksClient.infer call)

---

### Competition Readiness Checklist

Before claiming competition-ready, all of these must be verified:

- [ ] Input/output cardinality proven (test_end_to_end_cardinality.py passes)
- [ ] Fail-closed tests pass (test_fail_closed_behavior.py passes)
- [ ] 8-category benchmark results exist
- [ ] Overall accuracy >= target threshold
- [ ] Token usage within budget
- [ ] All production entrypoints verified
- [ ] No unreachable components in active runtime path
- [ ] No circular imports
- [ ] No duplicate task_ids in output
- [ ] Atomic write verified
- [ ] Schema validation verified
- [ ] Source_Of_Truth.md updated to match reality
