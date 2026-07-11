"""Artifact schema definitions."""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RunManifest:
    """Run manifest schema."""
    run_id: str
    phase: str
    status: str
    artifact_path: str
    created_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "phase": self.phase,
            "status": self.status,
            "artifact_path": self.artifact_path,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


@dataclass
class LatestPointer:
    """Latest pointer schema."""
    latest_run_id: str
    latest_phase: str
    latest_artifact: str
    created_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "latest_run_id": self.latest_run_id,
            "latest_phase": self.latest_phase,
            "latest_artifact": self.latest_artifact,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


@dataclass
class ArtifactIndex:
    """Artifact index schema."""
    run_id: str
    artifacts: list[str]
    created_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "artifacts": self.artifacts,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }
