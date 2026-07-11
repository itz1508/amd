# AMD Track 1 — Slide Deck

## Slide 1: Title

**AMD Track 1 Local-First Token Router**

A Dockerized benchmark agent for AMD Developer Hackathon Act II Track 1.

---

## Slide 2: Problem

Track 1 ranks submissions by **lowest recorded Fireworks token usage** after passing the accuracy gate.

The agent must:
- Stay compliant with the contest contract
- Read `/input/tasks.json`
- Write valid `/output/results.json`
- Minimize remote token consumption

---

## Slide 3: Solution

**Deterministic-first + Fireworks rescue architecture**

- Local deterministic tools when correctness is provable
- Input validation and output verification before acceptance
- Fireworks AI rescue only when model inference is required
- Remote calls routed exclusively through `FIREWORKS_BASE_URL`
- Model selection restricted to `ALLOWED_MODELS` at runtime

---

## Slide 4: Submission Artifact

**Image**
`ghcr.io/itz1508/amd-track1:latest`

**Digest**
`ghcr.io/itz1508/amd-track1@sha256:2a7dae4862a5c0216a169c984483aa5e47d3e31c09d71a6d2b070499a4996eed`

**Status**
- `linux/amd64`
- Public GHCR pull verified
- Minimized image (~46 MB)
- No bundled secrets
- Valid `/input` → `/output` smoke test passed

---

*Export this deck as a 4-slide PDF. No secrets. No private strategy files. Keep text readable.*
