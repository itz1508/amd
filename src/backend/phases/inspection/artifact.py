"""
Inspection artifact writer.
"""
from pathlib import Path
from typing import Any

from backend.artifact_store.writer import write_json_artifact, ArtifactWriteError


def write_inspection_artifact(path: Path, data: dict[str, Any]) -> None:
    """Write the 07_inspection.json artifact atomically.

    Args:
        path: Destination path for the artifact.
        data: Deterministic dictionary to serialize.

    Raises:
        ArtifactWriteError: If the artifact write fails.
    """
    write_json_artifact(path, data)