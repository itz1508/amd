# Source of truth

## Authority order

1. Latest explicit user instruction
2. This `Source_Of_Truth.md`
3. Project skills under `.agents/skills/`
4. Active repository code
5. Historical reports, old plans, and generated artifacts

`D:\Dev\amd` is the repository root.

Historical 9-phase AMD/Edge workflow text is not Track 1 authority unless the active code path proves it.

## Current objective

This repository is currently focused on the AMD Developer Hackathon ACT II Track 1 benchmark agent.

Track 1 objective:

```text
pass the accuracy gate first
then minimize Fireworks token usage
```

Target ambition:

```text
accuracy: 99 percent or better
Fireworks token use: under 5k when the hidden batch allows it
```

Do not sacrifice valid output, runtime reliability, or accuracy for token savings.

## Canonical runtime

The canonical runtime is the active Track 1 request-response path:

```text
/input/tasks.json
-> amd_track1/entrypoint.py
-> amd_track1/executor.py
-> amd_track1/router.py
-> amd_track1/tools/*
-> amd_track1/category_validator.py
-> amd_track1/tools/submission_validator.py
-> /output/results.json
```

Before claiming any behavior is active, inspect the production call path. Helper modules and helper-only tests do not prove runtime behavior.

## Runtime contract

The submitted container must:

```text
read /input/tasks.json
write /output/results.json
run non-interactively
exit within the judging runtime limit
run on linux/amd64
use injected environment variables for Fireworks calls
```

Required environment variables for remote inference:

```text
FIREWORKS_API_KEY
FIREWORKS_BASE_URL
ALLOWED_MODELS
```

No final-runtime dependency may require:

```text
OPENAI_API_KEY
ANTHROPIC_API_KEY
GEMINI_API_KEY
GOOGLE_API_KEY
MISTRAL_API_KEY
REQUESTY_API_KEY
OPENROUTER_API_KEY
```

Remote inference must go only through `FIREWORKS_BASE_URL`.

## Output contract

`/output/results.json` must have this shape:

```json
[
  {
    "task_id": "task-001",
    "answer": "string answer"
  }
]
```

Rules:

```text
every input task_id appears exactly once
no duplicate task_id
no missing task_id
no extra output fields
answer is always a string
output is written atomically
generated output is re-read and schema-validated before completion is claimed
```

Do not omit invalid tasks. If no valid answer can be produced, preserve the original `task_id` exactly once and emit a string fallback according to the active output contract.

## Canonical workflow

Expected Track 1 workflow:

```text
input validation
-> cheap category classification
-> deterministic tool if answer is provable
-> local validation
-> Fireworks solver only when needed
-> local validation
-> conditional verifier only for high-risk or invalid outputs
-> final local validation
-> strict output packing
-> atomic write
-> output re-read/schema validation
```

Deterministic tools must be conservative. A local tool may answer only when it can prove correctness; otherwise it must defer to model routing.

## Category set

Track 1 categories:

```text
factual_knowledge
mathematical_reasoning
sentiment_classification
text_summarisation
named_entity_recognition
code_debugging
logical_reasoning
code_generation
```

Runtime code must normalize category names carefully and must not silently invent incompatible alternatives.

## Routing policy

Preferred routing order:

```text
deterministic local tool
-> optional fully local packaged model if proven in the submitted container
-> cheapest sufficient Fireworks model from ALLOWED_MODELS
-> stronger Fireworks model only when needed
-> conditional verifier only when risk or validation requires it
```

Local model inference is optional. It is valid only when it runs fully inside the submitted container without non-Fireworks API keys or external model APIs.

Gemma is optional:

```text
Gemma through Fireworks: valid only if present in ALLOWED_MODELS
local Gemma: valid only if packaged/proven in the submitted container
```

Do not depend on `my-ai`, Codex CLI, Claude CLI, Gemini CLI, OpenAI API, Anthropic API, Mistral API, Requesty, OpenRouter, browser automation, or any other non-Fireworks cloud provider in final runtime.

## Fireworks policy

Every Fireworks call must:

```text
use FIREWORKS_BASE_URL
use FIREWORKS_API_KEY
select a model from ALLOWED_MODELS or an allowlist-validated role override
use temperature=0 unless a category explicitly requires creativity
use category-appropriate max_tokens
record prompt_tokens, completion_tokens, total_tokens when returned
record model_id, role, task_id, category, latency, and retry_count when logging exists
```

Retry transient transport/status errors only:

```text
429
500
502
503
504
connection errors
transport errors
timeouts
```

Do not retry permanent request/auth/model errors:

```text
400
401
404
422
```

Transport retries are separate from answer-correction retries and must not consume the limited correction budget.

All retry/backoff behavior must respect the total 600-second runtime budget.

## Conditional verifier policy

The verifier is not a default second call. It is a token-cost gate.

Call the verifier only when:

```text
category is high-risk
OR local validation fails
```

High-risk categories:

```text
code_generation
code_debugging
logical_reasoning
named_entity_recognition
```

Verifier requirements:

```text
call at most once per task
avoid circular imports between verifier.py and executor.py
reuse the executor Fireworks client or accept an injected client/callable
return strict JSON when structured output is supported
validate final_answer locally before replacing solver answer
fail closed on invalid verifier JSON
never replace a locally valid solver answer with invalid verifier output
```

## Current status

Machine-readable status is in `evidence/track1_current_status.json`.

### Verification status table

| # | Requirement | Status | Evidence | Result | Action |
|---|---|---|---|---|---|
| 1 | Conditional verifier integration | verified | test_conditional_verifier_integration.py (7 tests) | code_generation triggers verifier (1 solver + 1 verifier call) | Generalize to all high-risk categories |
| 2 | Verifier client ownership/circular dependency | verified | verifier.py line 335, executor.py line 26 | Local import avoids circular dependency; client passed as parameter | None |
| 3 | "What is 2+2?" routes to deterministic arithmetic | verified | test_end_to_end_cardinality.py, controlled tests | answer="4", model_used=None, solver_calls=0, verifier_calls=0 | None |
| 4 | Pipeline-level tests present | verified | pytest -q shows 312 tests passed | All repository tests pass including cardinality and fail-closed | Add edge cases |
| 5 | Entrypoint generates output file | verified | entrypoint --input input/tasks.json --output output/results.json | exit code 0, correct JSON generated, task count fixed | None |
| 6 | Input/output cardinality | verified | test_end_to_end_cardinality.py (3 tests) | Exact count match, no duplicates, no missing/extra task_ids | None |
| 7 | Invalid solver answer not preserved | partially_verified | VERIFICATION_POLICY.md, test_fail_closed_behavior.py | Policy: BLOCK if invalid + verifier failure | Runtime evidence needed |
| 8 | Malformed verifier response handled | partially_verified | VERIFICATION_POLICY.md, test_fail_closed_behavior.py | Policy: PRESERVE solver answer | Runtime evidence needed |
| 9 | Fail-closed behavior | partially_verified | VERIFICATION_POLICY.md decision matrix | Exact rules defined for all scenarios | Runtime evidence needed |
| 10 | Verifier max one pass | partially_verified | VERIFICATION_POLICY.md, test_fail_closed_behavior.py | Policy: at most one call per task | Runtime enforcement check needed |
| 11 | Solver/verifier model separation | verified | test_fail_closed_behavior.py::test_solver_verifier_model_separation | Different models enforced via model_roles.py | None |
| 12 | Verifier timeout/error behavior | partially_verified | test_fail_closed_behavior.py::test_verifier_timeout_error_behavior | Timeout handled without crash | More scenarios needed |
| 13 | Eight-category benchmark | unverified | input/eight_category_tasks.json created | 1/8 categories succeed (math); 7/8 require Fireworks | Needs real credentials |

#### Status summary
- **verified:** 6 requirements
- **partially_verified:** 6 requirements  
- **unverified:** 1 requirement (eight-category benchmark blocked by credentials)

### Evidence files

- `evidence/track1_current_status.json` - Machine-readable verification record (updated 2026-07-09T16:30:00Z)
- `evidence/edge_audit/edge_audit_20260709_1600/` - Edge repository audit artifacts
- `output/results.json` - Generated by entrypoint from input/tasks.json
- `input/eight_category_tasks.json` - 8-category test input
- `amd_track1/VERIFICATION_POLICY.md` - Fail-closed behavior and policy definitions
- Test outputs in `.pytest_cache`

### Recent changes

- **2026-07-09**: Fixed entrypoint.py bug (lines 122-127) - was counting JSON files in output directory instead of tasks in output file; now reads output file and counts tasks from JSON array
- **2026-07-09**: Added test_end_to_end_cardinality.py (3 tests) - verifies input/output cardinality, task_id uniqueness, no missing/extra IDs
- **2026-07-09**: Added test_fail_closed_behavior.py (5 tests) - verifies verifier behavior, model separation, timeout handling
- **2026-07-09**: Added VERIFICATION_POLICY.md - defines fail-closed behavior with decision matrix for all scenarios
- **2026-07-09**: Updated Source_Of_Truth.md with current status table
- **2026-07-09**: Updated evidence/track1_current_status.json with all verification results

## Required tests

For routing/verifier changes, required behavior tests include:

```text
deterministic math uses zero solver calls and zero verifier calls
low-risk valid solver answer skips verifier
high-risk category calls verifier exactly once
local validation failure calls verifier exactly once
invalid verifier JSON preserves locally valid solver answer
verifier final_answer failing local validation is rejected
all input task_id values appear exactly once
results contain only task_id and answer
real process_input or entrypoint smoke generates an output file
```

Required boundary tests:

```text
runtime code does not reference non-Fireworks cloud keys or provider URLs
runtime code does not import A-Flow or edge_backend
model role overrides do not bypass ALLOWED_MODELS unless a current contract explicitly allows it
transient Fireworks errors retry separately from correction retries
permanent Fireworks errors do not retry
```

## Completion evidence

Do not claim completion unless evidence is produced from `D:\Dev\amd`.

Completion reports must include:

```text
execution_root
git status before and after
git diff --name-status
changed files
commands run
stdout excerpt
stderr excerpt
exit code
sample input when pipeline behavior changes
actual generated output when pipeline behavior changes
output schema validation when output behavior changes
timed smoke result when runtime behavior changes
```

Reject completion when:

```text
claimed files do not exist
claimed tests do not exist
tests only call helper functions for active-runtime behavior
sample output was manually constructed
input task_id and output task_id differ
commands were not run from D:\Dev\amd
exit code is missing
runtime claim is based only on "no unbounded loops"
```

## Project skills

Use `.agents/skills/amd-track1-canonical/SKILL.md` for Track 1 runtime work, implementation handoffs, Fireworks routing, verifier wiring, Docker readiness, and completion evidence review.

Use `.agents/skills/plan-verify-authorize/SKILL.md` for plan validation, gap analysis, success definition, validation cases, and execution authorization before implementation.

Role labels are hints only. The task body controls the selected skill and action boundary.

## Useful commands

```powershell
# Run the AMD Track 1 test suite
C:\Python314\python.exe -m pytest amd_track1/tests -q

# Run verifier integration tests
C:\Python314\python.exe -m pytest amd_track1/tests/test_conditional_verifier_integration.py -q

# Run the Track 1 entrypoint with explicit paths
C:\Python314\python.exe -m amd_track1.entrypoint --input .\input\tasks.json --output D:\Temp\Edge\amd-track1-results.json --timeout 600
```

Use the repository's locked toolchain when it is working. If a fallback Python is used, report that explicitly.
