# AMD Track 1 Release Status

## Current result

Status: `amd_image_verified_locally`

- Canonical repository: `D:\Dev\amd`
- Branch: `main`
- Runtime source commit: `f14d111b3417990bd5c33ad9d22b84609bb6ba63`
- Full tests: 331 passed, exit code 0
- Production manifest: 53 files
- Immutable tag: `ghcr.io/itz1508/amd-track1:f14d111-final`
- Latest tag: `ghcr.io/itz1508/amd-track1:latest`
- Local image ID: `sha256:d4c468682761d4b5e801fcafb7000c2e4e47fe0237a02a3ddef7f0be57d0e03e`
- Platform: `linux/amd64`
- Entrypoint: `["python","-m","amd_track1.entrypoint"]`
- Local source/image hashes: 53/53 match
- Local deterministic execution: passed
- Real Fireworks execution: blocked
- Image push: not performed
- Anonymous public pull: not performed
- Public verification: not performed

## Remaining blocker

The endpoint and model are now known:

- `FIREWORKS_BASE_URL=https://inference.do-ai.run/v1`
- `ALLOWED_MODELS=gpt-4o`

The endpoint is reachable, but a live request using the existing
`FIREWORKS_API_KEY` returned HTTP 401. `MODEL_ACCESS_KEY` is absent from the
current environment, so the required credential is still unavailable.

Do not report `submission_ready` until real remote and mixed tests pass, both
tags are pushed with matching digests, anonymous pulls succeed, public hashes
match the manifest, and public deterministic/remote/mixed tests exit zero.
