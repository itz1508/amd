# AMD Repository Instructions

## Authority

- Canonical repository: `D:\Dev\amd`.
- Canonical Track 1 runtime: `D:\Dev\amd\amd_track1`.
- Canonical entrypoint: `python -m amd_track1.entrypoint`.
- Docker builds must use `D:\Dev\amd` as their context and
  `D:\Dev\amd\amd_track1\Dockerfile` as their Dockerfile.
- `D:\Dev\Edge` and `D:\Dev\amd-runtime-fix` are reference-only. Never build,
  tag, push, or promote runtime authority from them.
- The untracked `src/` backend pipeline is experimental residue and is excluded
  from the Track 1 release.

## Workflow records

- Every release run writes durable evidence under `evidence/release-current/`.
- Do not use TEMP as the authoritative location for plans, manifests, command
  output, validation results, or handoffs.
- Record command, output excerpt, exit code, touched paths, and interpretation.
- Do not report remote inference, publication, anonymous pull, or submission
  readiness without literal runtime evidence.

## Mutation boundary

- Inspect broadly and mutate narrowly.
- Preserve unrelated user changes.
- Stage only approved Track 1 runtime, tests, skills, tools, schemas,
  capabilities, packaging, authority, and release-evidence files.
- Never reset, clean, stash, or overwrite unrelated work.
- Do not create a second runtime entrypoint, state root, or source of truth.

## Track 1 release contract

- Input: `/input/tasks.json`.
- Output: `/output/results.json`.
- Preserve task IDs, cardinality, and input order.
- Every answer is a string.
- Deterministic arithmetic must work without Fireworks configuration.
- Remaining production inference uses only harness-provided
  `FIREWORKS_API_KEY`, `FIREWORKS_BASE_URL`, and `ALLOWED_MODELS`.
- Exact injected model IDs are preserved; no hardcoded fallback model is
  permitted.

## Validation gate

Before building or publishing:

1. Run the complete `amd_track1/tests` suite.
2. Run direct evaluator-style deterministic execution.
3. Generate the source manifest.
4. Build `linux/amd64` from `D:\Dev\amd`.
5. Verify entrypoint, packaged assets, hashes, and mounted container execution.
6. Run a real Fireworks smoke when all three harness variables are available.
7. Push only verified immutable and `latest` tags from the same image.

Never expose secrets.
