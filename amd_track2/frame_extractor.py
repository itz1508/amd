"""Bounded ffmpeg frame extraction for Track 2."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from amd_track2.video_probe import ProbeResult


@dataclass(frozen=True)
class FrameInfo:
    timestamp: float
    path: str
    role: str


@dataclass(frozen=True)
class ExtractionResult:
    success: bool
    frames: List[FrameInfo]
    error_message: str | None = None


class FrameExtractor:
    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg = ffmpeg_path

    def _compute_timestamps(self, duration: float) -> List[Tuple[float, str]]:
        if duration <= 0:
            return []
        points = [(0.5, "opening"), (0.2, "mid_20"), (0.4, "mid_40"),
                  (0.6, "mid_60"), (0.8, "mid_80"), (0.95, "closing")]
        result: List[Tuple[float, str]] = []
        for point, role in points:
            timestamp = min(0.5 if point == 0.5 else duration * point, duration)
            if not any(abs(timestamp - old) < 1e-6 for old, _ in result):
                result.append((timestamp, role))
        return result

    def _fallback_timestamps(self, video_path: str) -> List[Tuple[float, str]]:
        return [(float(i), f"fallback_{i}") for i in range(6)]

    def extract(self, video_path: str, probe: ProbeResult, output_dir: str | None = None) -> ExtractionResult:
        if not probe.success or not probe.has_video_stream:
            return ExtractionResult(False, [], "video stream unavailable")
        target = Path(output_dir or (Path(video_path).parent / "frames"))
        target.mkdir(parents=True, exist_ok=True)
        points = self._compute_timestamps(probe.duration_seconds or 0.0)
        if not points:
            points = self._fallback_timestamps(video_path)
        frames: List[FrameInfo] = []
        for index, (timestamp, role) in enumerate(points):
            path = target / f"frame_{index:03d}.jpg"
            cmd = [self.ffmpeg, "-y", "-ss", str(timestamp), "-i", video_path,
                   "-frames:v", "1", "-vf", "scale='min(1024,iw)':-2", "-q:v", "3", str(path)]
            result = subprocess.run(cmd, capture_output=True, timeout=30)
            if result.returncode == 0 and path.exists():
                frames.append(FrameInfo(timestamp, str(path), role))
        return ExtractionResult(bool(frames), frames, None if frames else "no frames extracted")

