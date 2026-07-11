"""Build structured visual evidence packets from extracted frames and metadata."""

import json
import logging
import os
import platform
import sys
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from amd_track2.frame_extractor import FrameInfo
from amd_track2.video_probe import ProbeResult

logger = logging.getLogger(__name__)


@dataclass
class FrameEntry:
    """A frame in the evidence packet."""

    timestamp: float
    path: str
    role: str
    sha256: Optional[str] = None


@dataclass
class VideoMetadata:
    """Sanitized video metadata."""

    duration_seconds: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    container_format: Optional[str] = None
    video_codec: Optional[str] = None


@dataclass
class EvidencePacket:
    """Complete visual evidence for one video task."""

    task_id: str
    video_url: str
    video_metadata: VideoMetadata
    frames: List[FrameEntry]
    requested_styles: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to plain dict for JSON compatibility."""
        return {
            "task_id": self.task_id,
            "video_url": self.video_url,
            "video_metadata": {
                k: v for k, v in asdict(self.video_metadata).items() if v is not None
            },
            "frames": [asdict(f) for f in self.frames],
            "requested_styles": self.requested_styles,
        }


@dataclass
class TaskEvidence:
    """Evidence for a single task execution."""

    task_id: str
    video: Optional[Dict[str, Any]] = None
    frames: Optional[List[Dict[str, Any]]] = None
    vision: Optional[Dict[str, Any]] = None
    captions: Optional[Dict[str, str]] = None
    gap_checks: Optional[Dict[str, Any]] = None
    repair_count: int = 0
    final_status: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for JSON output."""
        return {
            "task_id": self.task_id,
            "video": self.video,
            "frames": self.frames,
            "vision": self.vision,
            "captions": self.captions,
            "gap_checks": self.gap_checks,
            "repair_count": self.repair_count,
            "final_status": self.final_status,
        }


@dataclass
class FullEvidencePacket:
    """Complete evidence packet for a full run."""

    schema_version: str = "1.0"
    run_id: str = ""
    started_at: str = ""
    completed_at: str = ""
    input: Optional[Dict[str, Any]] = None
    runtime: Optional[Dict[str, Any]] = None
    tasks: Optional[List[Dict[str, Any]]] = None
    output: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.tasks is None:
            self.tasks = []

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for JSON output."""
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "input": self.input,
            "runtime": self.runtime,
            "tasks": self.tasks,
            "output": self.output,
            "result": self.result,
        }


class EvidencePacketBuilder:
    """Create EvidencePacket from probe and frame extraction results."""

    def build(
        self,
        task_id: str,
        video_url: str,
        probe: ProbeResult,
        frames: List[FrameInfo],
        requested_styles: List[str],
    ) -> EvidencePacket:
        """Assemble a complete evidence packet."""
        metadata = VideoMetadata(
            duration_seconds=probe.duration_seconds,
            width=probe.width,
            height=probe.height,
            fps=probe.fps,
            container_format=probe.container_format,
            video_codec=probe.video_codec,
        )

        frame_entries = [
            FrameEntry(timestamp=f.timestamp, path=f.path, role=f.role)
            for f in frames
        ]

        packet = EvidencePacket(
            task_id=task_id,
            video_url=video_url,
            video_metadata=metadata,
            frames=frame_entries,
            requested_styles=requested_styles,
        )

        logger.info(
            "Built evidence packet for %s: %d frames, styles=%s",
            task_id,
            len(frame_entries),
            requested_styles,
        )
        return packet


class EvidenceWriter:
    """Write complete evidence packets to file."""

    def __init__(self, evidence_dir: str = "/evidence"):
        self.evidence_dir = evidence_dir
        os.makedirs(evidence_dir, exist_ok=True)

    def write(
        self,
        packet: FullEvidencePacket,
        output_path: Optional[str] = None,
    ) -> Optional[str]:
        """Write evidence packet to JSON file atomically."""
        if not output_path:
            output_path = os.path.join(
                self.evidence_dir, f"track2-run-{packet.run_id}.json"
            )

        tmp_path = f"{output_path}.tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(packet.to_dict(), f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, output_path)
            logger.info("Wrote evidence packet to %s", output_path)
            return output_path
        except Exception as exc:
            logger.exception("Failed to write evidence packet")
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            return None

    @staticmethod
    def build_runtime_info(ffmpeg_path: Optional[str] = None, ffprobe_path: Optional[str] = None, vision_model: Optional[str] = None) -> Dict[str, Any]:
        """Build runtime information for evidence packet."""
        return {
            "python_version": sys.version,
            "platform": platform.platform(),
            "ffmpeg_path": ffmpeg_path,
            "ffprobe_path": ffprobe_path,
            "vision_model": vision_model,
        }


def compute_sha256(file_path: str) -> Optional[str]:
    """Compute SHA-256 hash of a file."""
    import hashlib

    try:
        with open(file_path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except Exception:
        return None


def generate_run_id() -> str:
    """Generate a unique run ID."""
    return uuid.uuid4().hex[:8]