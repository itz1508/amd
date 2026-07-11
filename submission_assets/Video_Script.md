# AMD Track 1 — Demo Video Script

**Target length:** 45–60 seconds (hard ceiling: 90 seconds)  
**Recording:** Terminal/browser screencast, no narration required  
**Platform:** Windows PowerShell (adjust paths accordingly)

---

## Shot Sequence

### Shot 1: GHCR Package Page (5 sec)
- Open browser to: `https://github.com/users/itz1508/packages/container/amd-track1`
- Show **Public** visibility badge
- Show package name `ghcr.io/itz1508/amd-track1`

### Shot 2: Anonymous Pull (10 sec)
- Terminal: `docker logout ghcr.io 2>$null`
- Terminal: `docker pull ghcr.io/itz1508/amd-track1:latest`
- Show pull progress completing

### Shot 3: Verify Digest (8 sec)
- Terminal:
  ```powershell
  docker inspect --format='{{index .RepoDigests 0}}' ghcr.io/itz1508/amd-track1:latest
  ```
- Confirm digest matches:
  `ghcr.io/itz1508/amd-track1@sha256:2a7dae4862a5c0216a169c984483aa5e47d3e31c09d71a6d2b070499a4996eed`

### Shot 4: Prepare Input (7 sec)
- Terminal:
  ```powershell
  mkdir demo-input, demo-output
  '[{"task_id":"demo-1","prompt":"What is 2+2? Return only the number."}]' | Set-Content demo-input/tasks.json -Encoding UTF8
  ```

### Shot 5: Run Container (15 sec)
- Terminal:
  ```powershell
  docker run --rm `
    -v "${PWD}/demo-input:/input:ro" `
    -v "${PWD}/demo-output:/output" `
    -e AMD_REMOTE_MODE=off `
    -e FIREWORKS_API_KEY=placeholder `
    -e FIREWORKS_BASE_URL=http://127.0.0.1:9 `
    -e ALLOWED_MODELS=placeholder-model `
    ghcr.io/itz1508/amd-track1:latest
  ```
- Show container executing and exiting cleanly

### Shot 6: Show Output (10 sec)
- Terminal: `Get-Content demo-output/results.json`
- Expected content contains:
  - `task_id`: `demo-1`
  - `answer`: `4`

---

## Acceptance Checklist

- [ ] GHCR image page visible
- [ ] Anonymous pull visible
- [ ] Digest visible and matches
- [ ] `docker run` command visible
- [ ] `results.json` visible with correct answer
- [ ] No real secrets shown (placeholder key only)
- [ ] Total duration under 90 seconds

---

## Notes

- Use deterministic task (`2+2`) so no external model call is required.
- `AMD_REMOTE_MODE=off` with placeholder env vars proves structural contract without live Fireworks usage.
- If recording on Linux/macOS, replace `${PWD}` with `$PWD` and `Set-Content` with `echo ... >`.
