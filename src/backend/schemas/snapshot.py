"""
Snapshot schema definitions.
"""
from dataclasses import dataclass
from typing import Any


@dataclass
class SnapshotNotice:
    """Represents a notice from capture (excluded paths, unreadable files, etc.)."""
    notice_code: str
    relative_path: str
    reason: str
    evidence: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "notice_code": self.notice_code,
            "relative_path": self.relative_path,
            "reason": self.reason,
            "evidence": self.evidence,
        }


@dataclass
class SnapshotFile:
    """Represents a captured file."""
    relative_path: str
    extension: str
    size_bytes: int
    sha256: str
    read_status: str  # "readable" or "unreadable"

    def to_dict(self) -> dict[str, Any]:
        return {
            "relative_path": self.relative_path,
            "extension": self.extension,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "read_status": self.read_status,
        }


@dataclass
class Snapshot_Output:
    """Snapshot phase output."""
    phase: str
    target_root: str
    status: str  # "completed" or "completed_with_notices"
    files: list["SnapshotFile"]
    notices: list["SnapshotNotice"]
    snapshot_fingerprint: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "target_root": self.target_root,
            "status": self.status,
            "files": [f.to_dict() for f in self.files],
            "notices": [n.to_dict() for n in self.notices],
            "snapshot_fingerprint": self.snapshot_fingerprint,
        }
