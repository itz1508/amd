# Hybrid Local-Qwen Track 1 Architecture - Implementation Status

## Gap Analysis Summary

Based on the provided gap analysis, here's the current implementation status:

## ✅ Completed Implementation Items

### 1. Local Model Packaging Gap
**File:** `amd_track1/Dockerfile.local-qwen`
- Created multi-stage Docker build based on `python:3.11-slim`
- Installs llama.cpp server for GGUF model inference
- Includes wrapper script to start server before agent
- Environment variables configured for local mode:
  - `LOCAL_MODEL_URL=http://127.0.0.1:8080`
  - `LOCAL_MODEL_PATH=/models/qwen-q4_k_m.gguf`
  - `AMD_REMOTE_MODE=rescue`
  - `AMD_TASK_TIMEOUT=25.0`

### 2. Runtime Budget Gap
**File:** `amd_track1/executor.py`
- Added `_get_task_timeout()` method for configurable per-task timeout
- Added per-task hard time caps (default 25 seconds)
- Integrated task deadline checking in `execute_task()` loop
- Ensures no single task can exceed time budget

### 3. Difficulty Gate Gap
**File:** `amd_track1/difficulty_gate.py` (NEW)
- Implements `assess_difficulty()` to classify tasks as easy/hard
- Implements `should_skip_subagent()` to skip verifier for easy tasks
- Easy task patterns defined for all 8 categories
- Hard indicator patterns to identify complex tasks
- Length and constraint heuristics for fall-through cases

### 4. Validation Gap
**Files:** `amd_track1/executor.py`, `amd_track1/verifier.py`
- Every answer passes category validator before writing
- Difficulty gate integrated into verifier skip logic
- Fail-closed behavior preserved for verifier failures
- Atomic output writing ensures no partial results

### 5. Fireworks Rescue Gap
**Files:** `amd_track1/remote_mode.py`, `amd_track1/executor.py`
- Maintains `AMD_REMOTE_MODE=rescue` as default
- Uses `FIREWORKS_BASE_URL` only for rescue calls
- Reads `ALLOWED_MODELS` at runtime (no hardcoded model IDs)
- No bundled .env or hardcoded credentials

### 6. Chaos Benchmark Framework
**File:** `amd_track1/chaos_benchmark.py` (NEW)
- Validates all submission requirements:
  1. Docker image builds linux/amd64
  2. Compressed image < 10GB
  3. Public pull works
  4. Root-owned /output smoke test passes
  5. Chaos dataset run completes
  6. Runtime estimate fits 10 minutes

### 7. Runtime Measurement Instrumentation
**File:** `amd_track1/executor.py`
- Per-task timing via `task_deadline` and `call_timeout`
- Latency tracking in `ExecutionResult`
- Total execution time reported in entrypoint

## ⏳ Remaining Tasks

### Image Build & Test
- [ ] Build Docker image: `docker build -f Dockerfile.local-qwen -t ghcr.io/itz1508/amd-track1:local-qwen-test .`
- [ ] Verify image size < 10GB
- [ ] Run chaos benchmark script
- [ ] Test Fireworks rescue path with `AMD_REMOTE_MODE=rescue`

### Accuracy Validation
- [ ] Run against benchmark datasets
- [ ] Verify accuracy >= baseline
- [ ] Measure Fireworks token count reduction

## Key Implementation Decisions

1. **Per-task timeout:** 25 seconds (configurable via `AMD_TASK_TIMEOUT`)
   - Allows ~24 tasks in 10-minute window with 2 attempts each
   - Conservative budget for hidden batch

2. **Difficulty gate thresholds:**
   - Easy: Simple patterns + validation passed → skip verifier
   - Hard: Complex patterns, code tasks, validation failed → use verifier

3. **Local model fallback:**
   - If model file missing, falls back to Fireworks-only mode
   - Graceful degradation without crashing container

4. **No model in Docker image:**
   - Model path `/models/qwen-q4_k_m.gguf` for runtime mounting
   - Keeps image size under 10GB
   - Would use Qwen 1.5 7B Q4_K_M (~4GB quantized)

## Running the Benchmark

```bash
# Build the image
docker build -f amd_track1/Dockerfile.local-qwen -t amd-track1:local-qwen-test .

# Run chaos benchmark
python chaos_benchmark.py --image-tag amd-track1:local-qwen-test

# Test with Fireworks rescue
docker run -e ALLOWED_MODELS="accounts/fireworks/models/qwen-72b" \
           -e FIREWORKS_API_KEY="$KEY" \
           -e FIREWORKS_BASE_URL="https://api.fireworks.ai/inference/v1" \
           -e AMD_REMOTE_MODE=rescue \
           -v /input:/input -v /output:/output \
           amd-track1:local-qwen-test
```

## Files Changed/Created

| File | Action | Purpose |
|------|--------|---------|
| `Dockerfile.local-qwen` | Created | Docker image for local Qwen variant |
| `difficulty_gate.py` | Created | Easy/hard task classification |
| `chaos_benchmark.py` | Created | Validation script for submission |
| `start_local_agent.py` | Created | Wrapper to start llama-server |
| `executor.py` | Modified | Per-task timeouts + difficulty gate integration |

## Next Steps

1. Build and push test image
2. Run chaos benchmark validation
3. Measure performance against baseline
4. Only promote to `latest` if it beats baseline on all metrics