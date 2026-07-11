"""
Analysis_Classification artifact writer.

Writes 03_analysis_classification.json atomically outside the scanned target.
"""
from pathlib import Path
from typing import Any

from backend.artifact_store.writer import write_json_artifact, ArtifactWriteError


ARTIFACT_FILENAME = "03_analysis_classification.json"


def write_analysis_classification_artifact(
    output_root: str | Path,
    data: dict[str, Any],
) -> Path:
    """Write the Analysis_Classification artifact atomically.

    Args:
        output_root: Directory for the artifact (must be outside target).
        data: Serialized Analysis_Classification_Output dictionary.

    Returns:
        Path to the written artifact.

    Raises:
        ArtifactWriteError: If the write fails.
    """
    output_path = Path(output_root).resolve()
    output_path.mkdir(parents=True, exist_ok=True)
    artifact_path = output_path / ARTIFACT_FILENAME

    try:
        write_json_artifact(artifact_path, data)
    except ArtifactWriteError:
        raise
    except Exception as e:
        raise ArtifactWriteError(f"Failed to write artifact {artifact_path}: {e}") from e

    return artifact_path