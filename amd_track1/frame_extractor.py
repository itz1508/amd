"""
frame_extractor.py

Track 2 (Video Captioning) tool: downloads a video from a URL and extracts
keyframes as images, ready to hand to Agent B (context extraction).

Zero LLM tokens — this is pure download + video processing (ffmpeg),
same "tools do the deterministic work, LLM only reasons over the result"
principle as the rest of this build.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

import requests

REQUEST_TIMEOUT = 60  # video downloads can be slow; clips are 30s-2min


def download_video(url: str, dest_dir: Path) -> Path:
    """Download the video file from a URL to a local path."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = url.split("/")[-1].split("?")[0] or "clip.mp4"
    dest_path = dest_dir / filename

    resp = requests.get(url, stream=True, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    with open(dest_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    return dest_path


def extract_keyframes(
    video_path: Path,
    output_dir: Path,
    frames_per_video: int = 8,
) -> list[Path]:
    """
    Extract evenly-spaced keyframes from the video using ffmpeg.

    frames_per_video=8 is a reasonable default: enough to capture scene
    changes across a 30s-2min clip without generating so many frames that
    Agent B's context call becomes expensive/slow.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get video duration first, so frames are evenly spaced across the clip
    duration = _get_duration_seconds(video_path)
    if duration <= 0:
        duration = 60  # fallback assumption if ffprobe fails

    interval = duration / (frames_per_video + 1)

    frame_paths = []
    for i in range(1, frames_per_video + 1):
        timestamp = interval * i
        frame_path = output_dir / f"frame_{i:03d}.jpg"
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(timestamp),
            "-i", str(video_path),
            "-frames:v", "1",
            "-q:v", "2",
            str(frame_path),
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        if result.returncode == 0 and frame_path.exists():
            frame_paths.append(frame_path)

    return frame_paths


def _get_duration_seconds(video_path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return float(result.stdout.strip())
    except Exception:
        return -1.0


def extract_frames_from_url(
    video_url: str,
    frames_per_video: int = 8,
    work_dir: str | None = None,
) -> list[str]:
    """
    Public entry point: video URL in, list of local frame image paths out.

    Usage:
        frame_paths = extract_frames_from_url("https://.../clip.mp4")
        # hand frame_paths to Agent B for context extraction
    """
    tmp_root = Path(work_dir) if work_dir else Path(tempfile.mkdtemp(prefix="track2_"))
    video_path = download_video(video_url, tmp_root / "video")
    frames_dir = tmp_root / "frames"
    frame_paths = extract_keyframes(video_path, frames_dir, frames_per_video=frames_per_video)
    return [str(p) for p in frame_paths]


if __name__ == "__main__":
    import json
    import sys

    url = sys.argv[1] if len(sys.argv) > 1 else None
    if not url:
        print("Usage: python frame_extractor.py <video_url>")
        sys.exit(1)

    frames = extract_frames_from_url(url)
    print(json.dumps({"frame_count": len(frames), "frames": frames}, indent=2))
