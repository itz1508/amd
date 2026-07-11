# AMD Track 1 Emergency Release Request

## Objective

Recover one authoritative AMD Track 1 release from `D:\Dev\amd`, preserve a
durable workflow record, validate the evaluator contract, build only from AMD,
and publish only when source, image, runtime, and public provenance are proven.

## Scope

Included: Track 1 runtime, production skills, tools, schemas, capabilities,
directly relevant tests, Docker packaging, authority files, and release
evidence.

Excluded: Edge mutation, amd-runtime-fix mutation, Track 2, local-Qwen,
benchmarks, the untracked `src` pipeline, historical reports, temporary outputs,
and unrelated submission assets.

## Requested final outcome

`submission_ready` only after full tests, real Fireworks inference, local and
public image provenance, matching immutable/latest digests, anonymous pull, and
public deterministic/remote/mixed tests all pass.
