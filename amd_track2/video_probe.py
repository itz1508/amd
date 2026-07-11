"""Inspect downloaded video with ffprobe before frame extraction."""

import json
import logging
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from amd_track2.ffmpeg_resolver import FFprobeResolutionError, resolve_ffprobe

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProbeResult:
    """Structured ffprobe output."""

    success: bool
    duration_seconds: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    container_format: Optional[str] = None
    video_codec: Optional[str] = None
    has_video_stream: bool = False
    error_message: Optional[str] = None
    raw_streams: Optional[List[Dict[str, Any]]] = None


class VideoProbe:
    """Wrap ffprobe to extract safe metadata."""

    def __init__(self, ffprobe_path: Optional[str] = None):
        # Use deterministic resolution: resolve at init time
        try:
            self.ffprobe = resolve_ffprobe(ffprobe_path)
        except FFprobeResolutionError:
            # Store None to indicate resolution failure - will fail on first probe
            self.ffprobe = None

    def _get_ffprobe(self) -> str:
        """Get ffprobe path, raising explicit error if not resolved."""
        if self.ffprobe is None:
            raise FFprobeResolutionError(
                "ffprobe not found. Set FFPROBE_PATH environment variable or provide explicit path."
            )
        return self.ffprobe

    def probe(self, local_path: str) -> ProbeResult:
        """Run ffprobe and return structured metadata."""
        # Verify ffprobe is available early
        try:
            ffprobe_path = self._get_ffprobe()
        except FFprobeResolutionError as exc:
            return ProbeResult(
                success=False,
                error_message=str(exc),
            )

        try:
            cmd = [
                ffprobe_path,
                "-v",
                "error",
                "-print_format",
                "json",
                "-show_streams",
                "-show_format",
                local_path,
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                logger.warning("ffprobe failed: %s", result.stderr)
                return ProbeResult(
                    success=False,
                    error_message=result.stderr.strip() or "ffprobe non-zero exit",
                )

            data = json.loads(result.stdout)
            return self._parse(data)
        except subprocess.TimeoutExpired:
            return ProbeResult(
                success=False, error_message="ffprobe timed out after 30s"
            )
        except FFprobeResolutionError:
            return ProbeResult(
                success=False, error_message="ffprobe unavailable"
            )
        except Exception as exc:
            logger.exception("ffprobe exception")
            return ProbeResult(success=False, error_message=str(exc))

    def _parse(self, data: Dict[str, Any]) -> ProbeResult:
        """Parse ffprobe JSON into ProbeResult."""
        streams = data.get("streams", [])
        video_streams = [s for s in streams if s.get("codec_type") == "video"]
        fmt = data.get("format", {})

        if not video_streams:
            return ProbeResult(
                success=False,
                error_message="No video stream found",
                raw_streams=streams,
            )

        vs = video_streams[0]
        duration: Optional[float] = None

        # Duration from format first, then stream
        dur_str = fmt.get("duration") or vs.get("duration")
        if dur_str:
            try:
                duration = float(dur_str)
            except ValueError:
                pass

        # Fallback: nb_frames / fps
        if duration is None or duration <= 0:
            nb_frames = vs.get("nb_frames")
            fps = self._parse_fps(vs.get("r_frame_rate", ""))
            if nb_frames and fps and fps > 0:
                try:
                    duration = int(nb_frames) / fps
                except (ValueError, ZeroDivisionError):
                    pass

        width = self._int_or_none(vs.get("width"))
        height = self._int_or_none(vs.get("height"))
        fps = self._parse_fps(vs.get("r_frame_rate", ""))
        container = fmt.get("format_name")
        codec = vs.get("codec_name")

        return ProbeResult(
            success=True,
            duration_seconds=duration,
            width=width,
            height=height,
            fps=fps,
            container_format=container,
            video_codec=codec,
            has_video_stream=True,
            raw_streams=streams,
        )

    @staticmethod
    def _int_or_none(value: Any) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_fps(r_frame_rate: str) -> Optional[float]:
        if not r_frame_rate:
            return None
        try:
            if "/" in r_frame_rate:
                num, den = r_frame_rate.split("/", 1)
                return float(num) / float(den)
            return float(r_frame_rate)
        except (ValueError, ZeroDivisionError):
            return None