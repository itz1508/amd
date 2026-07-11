"""Artifact index utilities."""
from typing import Any


def create_artifact_index(artifacts: list[str]) -> dict[str, Any]:
    """Create an artifact index."""
    return {"artifacts": artifacts, "count": len(artifacts)}


def compute_artifact_hashes(artifacts: list[str]) -> dict[str, str]:
    """Compute hashes for artifacts."""
    return {artifact: "placeholder_hash" for artifact in artifacts}
