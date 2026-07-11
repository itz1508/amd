"""
Scan schema definitions.
"""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Scan_File:
    """Represents a scanned file with classification."""
    relative_path: str
    file_type: str  # "source", "test", "config", "build", "data", "other"
    language: str | None  # e.g., "python", "json", "toml", "markdown"
    size_bytes: int
    sha256: str
    category: str  # "package", "module", "script", "config", "test", "data", "documentation"
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "relative_path": self.relative_path,
            "file_type": self.file_type,
            "language": self.language,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "category": self.category,
        }


@dataclass
class Scan_Surface:
    """Represents a repository surface (entry point, package, etc.)."""
    surface_type: str  # "entry_point", "package", "module", "class", "function"
    identifier: str
    source_path: str
    evidence: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "surface_type": self.surface_type,
            "identifier": self.identifier,
            "source_path": self.source_path,
            "evidence": self.evidence,
        }


@dataclass
class Scan_Notice:
    """Represents a scan notice (unreadable, excluded, etc.)."""
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
class Scan_Output:
    """Scan phase output."""
    phase: str
    snapshot_fingerprint: str
    target_root: str
    status: str  # "completed" or "completed_with_notices"
    files: list[Scan_File] = field(default_factory=list)
    surfaces: list[Scan_Surface] = field(default_factory=list)
    notices: list[Scan_Notice] = field(default_factory=list)
    scan_fingerprint: str = ""
    language_summary: dict[str, int] = field(default_factory=dict)
    surface_summary: dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "snapshot_fingerprint": self.snapshot_fingerprint,
            "target_root": self.target_root,
            "status": self.status,
            "files": [f.to_dict() for f in self.files],
            "surfaces": [s.to_dict() for s in self.surfaces],
            "notices": [n.to_dict() for n in self.notices],
            "scan_fingerprint": self.scan_fingerprint,
            "language_summary": self.language_summary,
            "surface_summary": self.surface_summary,
        }
