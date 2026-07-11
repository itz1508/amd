# Video Recording Blocker Report

**Date:** 2026-07-10  
**Status:** Demo video NOT recorded — tooling unavailable in this environment

---

## Why Video Could Not Be Recorded

| Blocker | Detail |
|---------|--------|
| Environment | Headless agent session — no screen recording capability |
| No OBS/ShareX | No screen capture software installed |
| No browser automation | Cannot drive browser + terminal simultaneously for recording |
| No ffmpeg | Not available for CLI-based capture |

---

## Exact Recording Commands (for manual execution)

### Platform: Windows PowerShell

**Step 1 — Open GHCR page**
```powershell
Start-Process "https://github.com/users/itz1508/packages/container/amd-track1"
```
Show the **Public** visibility badge and package name.

**Step 2 — Anonymous pull**
```powershell
docker logout ghcr.io 2>$null
docker pull ghcr.io/itz1508/amd-track1:latest
```

**Step 3 — Verify digest**
```powershell
docker inspect --format='{{index .RepoDigests 0}}' ghcr.io/itz1508/amd-track1:latest
```
Confirm output matches:
```
ghcr.io/itz1508/amd-track1@sha256:2a7dae4862a5c0216a169c984483aa5e47d3e31c09d71a6d2b070499a4996eed
```

**Step 4 — Prepare demo input**
```powershell
mkdir demo-input, demo-output
'[{"task_id":"demo-1","prompt":"What is 2+2? Return only the number."}]' | Set-Content demo-input/tasks.json -Encoding UTF8
```

**Step 5 — Run container**
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

**Step 6 — Show output**
```powershell
Get-Content demo-output/results.json
```
Expected content contains:
- `task_id`: `demo-1`
- `answer`: `4`

---

## Recommended Recording Tools

| Tool | Platform | Use |
|------|----------|-----|
| OBS Studio | Windows/Linux/macOS | Free, full control, export MP4 |
| ShareX | Windows | Lightweight, region capture, auto-upload |
| QuickTime Player | macOS | Built-in, New Screen Recording |
| SimpleScreenRecorder | Linux | Free, configurable |
| Loom | Any (browser) | Quick, generates shareable link |

---

## Video Acceptance Checklist (verify after recording)

- [ ] GHCR image page visible
- [ ] Anonymous `docker pull` visible
- [ ] Digest visible and matches `sha256:330144...`
- [ ] `docker run` command visible
- [ ] `results.json` visible with correct answer
- [ ] No real secrets shown (placeholder key only)
- [ ] Total duration under 90 seconds

---

## Hosting Recommendation

Upload the recorded MP4 to:
- **YouTube Unlisted** — free, reliable, direct link for submission form
- **Google Drive** — shareable link, no compression

---

*Once recorded and uploaded, paste the video URL into `Submission_Form_Values.md` and commit the update.*
