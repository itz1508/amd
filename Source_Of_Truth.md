# AMD Project Source of Truth

## Authority boundary

Operational rules for coding agents live only in [`AGENTS.md`](AGENTS.md). This document is the project architecture and verification record; it does not restate agent-governance rules.

Repository root: `D:\Dev\amd`
Obsolete project reference: `D:\Dev\Edge` (do not copy from it without explicit reauthorization).

Release evidence root: `D:\Dev\amd\evidence\release-current`.

The `src/` backend pipeline currently present in the working tree is not part
of the committed repository history and is not a canonical release surface.
It must not authorize cleanup, mutation, packaging, or release decisions.

`D:\Dev\amd-runtime-fix` and `D:\Dev\Edge` are reference-only working copies
of the AMD Git repository. They are not valid Docker build contexts or release
authorities.

## Active deliverables

### Track 1

The production Track 1 runtime is `amd_track1.entrypoint` and follows:

```text
/input/tasks.json
-> input validation
-> category classification
-> deterministic tool when provably eligible
-> Fireworks for remaining tasks
-> category validation
-> atomic /output/results.json
```

Production inference is Fireworks-only. Experimental local-Qwen files are not part of the production submission path or image.

Supported categories:

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

### Track 2

Track 2 is an independent video-captioning package under `amd_track2`:

```text
tasks.json
-> video fetch and probe
-> frame extraction
-> Fireworks vision context extraction
-> four-style caption generation
-> caption gap validation
-> atomic results.json
```

Track 1 executor/router code is not a Track 2 dependency.

## Runtime contracts

Required inference variables are injected at runtime:

```text
FIREWORKS_API_KEY
FIREWORKS_BASE_URL
ALLOWED_MODELS
```

No API key, provider hostname, model identifier, allowed-model list, developer path, registry credential, or model file is bundled in production images.

Track 1 output:

```json
[
  {"task_id": "task-001", "answer": "string"}
]
```

Track 2 output:

```json
[
  {"task_id": "video-001", "captions": {"formal": "...", "sarcastic": "...", "humorous_tech": "...", "humorous_non_tech": "..."}}
]
```

Every valid input task must appear exactly once. Answers/captions are strings, output is atomically written, and generated output is re-read and schema-validated.

## Fireworks behavior

Each client normalizes the injected base URL in one location and emits exactly one `/chat/completions` suffix. Models are selected only from parsed `ALLOWED_MODELS`. Transient transport, timeout, connection, 429, and 5xx failures may retry; permanent 4xx/auth/model failures do not.

## Verification requirements

Import success is not runtime proof. Applicable validation must include:

- focused tests and the complete applicable Track suite;
- compile/import checks;
- actual entrypoint execution;
- mounted `/input` and `/output` container smoke;
- `linux/amd64` image verification;
- live Fireworks smoke when valid credentials are available.

Mocked requests and structural-only runs must be labeled as mocked or structural. Do not claim live inference, registry publication, or submission readiness without command output and exit-code evidence.

## Current verification record

The repository is dirty with unrelated historical and experimental artifacts. The active runtime edits are not a publication claim. Current verified local checks are recorded in command output and should be rerun after any runtime change; stale reports and generated artifacts are not authority.

The public image digest recorded by earlier verification is historical reference only. It must not be treated as the current image unless an anonymous pull and digest comparison are rerun.

## Change ownership

- Track 1 runtime and tests: `amd_track1/`
- Track 2 runtime and tests: `amd_track2/`
- Benchmark fixtures and reports remain outside production runtime paths.

The current emergency release scope is Track 1 only. Track 2, local-Qwen,
benchmarks, generated reports, temporary fixtures, historical bundles, and the
untracked backend pipeline are excluded from the Track 1 image.

When architecture and code disagree, inspect the active entrypoint and call path, then update this document with runtime evidence. Do not add a second authority file.
