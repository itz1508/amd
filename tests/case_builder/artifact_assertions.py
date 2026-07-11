"""
Generic assertions for phase artifact properties.

These helpers accept phase-specific field configuration to avoid hardcoding
fields belonging to any single phase.
"""
import json
from pathlib import Path
from typing import Any


def assert_artifact_exists_and_valid_json(path: Path) -> dict[str, Any]:
    """Assert the artifact exists and is valid UTF-8 JSON."""
    assert path.exists(), f"Artifact not found: {path}"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, dict)
    return data


def assert_artifact_deterministic(path: Path) -> None:
    """Assert that the artifact serializes deterministically by re-reading it."""
    with open(path, "r", encoding="utf-8") as f:
        first = f.read()
    with open(path, "r", encoding="utf-8") as f:
        second = f.read()
    assert first == second
    data = json.loads(first)
    reserialized = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert reserialized == json.dumps(
        json.loads(reserialized), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def assert_artifact_has_required_fields(
    path: Path,
    required_fields: list[str],
    phase_name: str | None = None,
) -> None:
    """Assert the artifact contains all required fields for a given phase.
    
    Args:
        path: Path to the artifact JSON file
        required_fields: List of field names that must be present
        phase_name: Optional phase name for error messages
    """
    data = assert_artifact_exists_and_valid_json(path)
    phase_desc = f" {phase_name}" if phase_name else ""
    for field in required_fields:
        assert field in data, f"Missing required field{phase_desc}: {field}"