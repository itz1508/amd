"""
Atomic artifact writer for snapshot phase.
"""
import json
import tempfile
from pathlib import Path
from typing import Any


class ArtifactWriteError(Exception):
    """Error writing artifact file."""
    pass


def write_json_artifact(path: Path, data: dict[str, Any]) -> None:
    """Write JSON artifact atomically.
    
    Uses temporary file under same directory, then atomic replacement.
    Guarantees deterministic key ordering.
    
    Args:
        path: Destination path for artifact.
        data: Data dictionary to serialize.
        
    Raises:
        ArtifactWriteError: If write fails.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create temp file in same directory for atomic rename
    fd, temp_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=".tmp_",
        suffix=".json"
    )
    
    try:
        with open(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, sort_keys=True)
        
        # Atomic replacement
        Path(temp_path).replace(path)
    except Exception as e:
        # Clean up temp file on failure
        try:
            Path(temp_path).unlink(missing_ok=True)
        finally:
            raise ArtifactWriteError(f"Failed to write artifact {path}: {e}") from e