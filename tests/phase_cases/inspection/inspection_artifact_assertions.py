"""Assertions for Inspection artifact properties."""
import json
from pathlib import Path


def assert_inspection_artifact_exists_and_valid_json(path: Path) -> dict:
    """Assert the Inspection artifact exists and is valid UTF-8 JSON."""
    assert path.exists(), f"Artifact not found: {path}"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, dict)
    return data


def assert_inspection_artifact_deterministic(path: Path) -> None:
    """Assert that the Inspection artifact serializes deterministically by re-reading it."""
    with open(path, "r", encoding="utf-8") as f:
        first = f.read()
    with open(path, "r", encoding="utf-8") as f:
        second = f.read()
    assert first == second
    data = json.loads(first)
    reserialized = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert reserialized == json.dumps(json.loads(reserialized), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def assert_inspection_artifact_has_required_fields(path: Path) -> None:
    """Assert the Inspection artifact contains all required Inspection_Output fields."""
    data = assert_inspection_artifact_exists_and_valid_json(path)
    required = [
        "phase",
        "status",
        "terminal_state",
        "inspection_id",
        "source_phase",
        "source_status",
        "source_fingerprint",
        "gap_evaluation_fingerprint",
        "simulation_environment_fingerprint",
        "inspection_passed",
        "checks",
        "findings",
        "failure_reasons",
        "dossier_evidence_refs",
        "route_history",
        "real_target_unchanged",
        "unresolved_conflict",
        "regression_detected",
        "next_route",
        "inspection_fingerprint",
        "metadata",
    ]
    for field in required:
        assert field in data, f"Missing required field: {field}"