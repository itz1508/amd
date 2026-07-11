# AMD Track 1 Submission Assets

**Date:** 2026-07-10  
**Image:** `ghcr.io/itz1508/amd-track1:latest`  
**Digest:** `ghcr.io/itz1508/amd-track1@sha256:2a7dae4862a5c0216a169c984483aa5e47d3e31c09d71a6d2b070499a4996eed`

---

## Files in This Package

| File | Purpose |
|------|---------|
| `AMD_Track1_Slides.md` | 4-slide deck content (copy into Google Slides / PowerPoint / Keynote, then export PDF) |
| `Video_Script.md` | Shot-by-shot demo video script with PowerShell commands |
| `Submission_Form_Values.md` | All form fields ready for copy-paste into submission portal |

---

## Quick Reference: Form Values

### Image
```
ghcr.io/itz1508/amd-track1:latest
```

### Digest
```
ghcr.io/itz1508/amd-track1@sha256:2a7dae4862a5c0216a169c984483aa5e47d3e31c09d71a6d2b070499a4996eed
```

### Short Description
Local-first AMD Track 1 agent that solves tasks with deterministic tools first and uses Fireworks AI rescue routing only when needed to preserve accuracy while minimizing tokens.

### Long Description
This project is a Track 1 benchmark agent designed for the AMD Developer Hackathon Act II. It reads the provided `/input/tasks.json`, classifies each task, applies deterministic local tools when correctness is provable, and falls back to Fireworks AI only when a task requires model inference or local validation cannot safely accept the result. The runtime enforces the contest contract by writing a valid `/output/results.json` with exact `task_id` and `answer` fields. Remote calls use only `FIREWORKS_BASE_URL`, `FIREWORKS_API_KEY`, and models from `ALLOWED_MODELS` at runtime. The goal is to pass the accuracy gate while keeping recorded Fireworks token usage low.

### Category
Track 1: Hybrid Token-Efficient Routing Agent

### Technologies
Python, Docker, Fireworks AI, GitHub Container Registry, JSON validation, pytest

---

## Success Criteria

| Criterion | Status |
|-----------|--------|
| S1: Video proves public container pull and `/input` → `/output` run | ⬜ Record video per `Video_Script.md` |
| S2: Slides explain strategy without exposing private tests/benchmarks | ⬜ Export `AMD_Track1_Slides.md` to PDF |
| S3: Submission copy does not overclaim self-contained Qwen/local model | ✅ Qwen3/llama.cpp excluded from public technologies |
| S4: All form fields ready | ✅ See `Submission_Form_Values.md` |
| S5: No secrets, tokens, or private files in video/slides | ✅ Verified in scripts |

---

## Next Steps

1. **Slides:** Open `AMD_Track1_Slides.md`, copy each slide into your preferred tool, export as 4-page PDF.
2. **Video:** Follow `Video_Script.md` shot sequence, record screen, trim to 45–60 seconds.
3. **Upload:** Host video (YouTube unlisted or Google Drive) and slides PDF.
4. **Submit:** Copy values from `Submission_Form_Values.md` into the AMD Track 1 submission form.
