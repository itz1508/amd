# AMD Track 1 — Submission Form Values

## Image & Digest

| Field | Value |
|-------|-------|
| **Docker Image** | `ghcr.io/itz1508/amd-track1:latest` |
| **Immutable Digest** | `ghcr.io/itz1508/amd-track1@sha256:2a7dae4862a5c0216a169c984483aa5e47d3e31c09d71a6d2b070499a4996eed` |
| **Platform** | `linux/amd64` |
| **Size** | ~46 MB |

---

## Short Description (1–2 sentences)

Local-first AMD Track 1 agent that solves tasks with deterministic tools first and uses Fireworks AI rescue routing only when needed to preserve accuracy while minimizing tokens.

---

## Long Description (paragraph)

This project is a Track 1 benchmark agent designed for the AMD Developer Hackathon Act II. It reads the provided `/input/tasks.json`, classifies each task, applies deterministic local tools when correctness is provable, and falls back to Fireworks AI only when a task requires model inference or local validation cannot safely accept the result. The runtime enforces the contest contract by writing a valid `/output/results.json` with exact `task_id` and `answer` fields. Remote calls use only `FIREWORKS_BASE_URL`, `FIREWORKS_API_KEY`, and models from `ALLOWED_MODELS` at runtime. The goal is to pass the accuracy gate while keeping recorded Fireworks token usage low.

---

## Category

**Track 1: Hybrid Token-Efficient Routing Agent**

---

## Technologies Used

```
Python
Docker
Fireworks AI
GitHub Container Registry
JSON validation
pytest
```

> **Note:** `llama.cpp` and `Qwen3` were used during local development and validation, but are **not bundled in the submitted container image**. List them only if the form explicitly allows "development/validation tools" as a separate field.

---

## Video

| Field | Value |
|-------|-------|
| **Video URL** | *(To be uploaded: unlisted YouTube or Google Drive link)* |
| **Length** | 45–60 seconds (max 90) |
| **Content** | Anonymous GHCR pull → digest verify → `docker run` → `results.json` output |

---

## Slides

| Field | Value |
|-------|-------|
| **Slides URL** | *(To be uploaded: PDF or Google Drive link)* |
| **Format** | 4-slide PDF |
| **Content** | Title → Problem → Solution → Submission Artifact |

---

## Hosting Plan

| Asset | Target | Status |
|-------|--------|--------|
| Video | YouTube Unlisted or Google Drive | ⬜ Pending upload |
| Slides | Google Drive or direct PDF upload | ⬜ Pending upload |

---

## Pre-Upload Checklist

- [ ] Video shows public GHCR page
- [ ] Video shows anonymous `docker pull`
- [ ] Video shows digest match
- [ ] Video shows `docker run` with placeholder env (no real secrets)
- [ ] Video shows `results.json` with correct answer
- [ ] Video duration under 90 seconds
- [ ] Slides exported as PDF
- [ ] Slides contain no secrets or private strategy details
- [ ] Slides use exact image URL and digest
- [ ] Form descriptions do not overclaim self-contained local model behavior
- [ ] Technologies list excludes Qwen3/llama.cpp unless development-only field exists
