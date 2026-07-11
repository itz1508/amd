"""Assertions for Analysis_Classification artifact properties."""
import json
from pathlib import Path


def assert_analysis_classification_artifact_exists_and_valid_json(path: Path) -> dict:
    """Assert the Analysis_Classification artifact exists and is valid UTF-8 JSON."""
    assert path.exists(), f"Artifact not found: {path}"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, dict)
    return data


def assert_analysis_classification_artifact_deterministic(path: Path) -> None:
    """Assert that the Analysis_Classification artifact serializes deterministically by re-reading it."""
    with open(path, "r", encoding="utf-8") as f:
        first = f.read()
    with open(path, "r", encoding="utf-8") as f:
        second = f.read()
    assert first == second
    data = json.loads(first)
    reserialized = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert reserialized == json.dumps(json.loads(reserialized), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def assert_analysis_classification_artifact_has_required_fields(path: Path) -> None:
    """Assert the Analysis_Classification artifact contains all required Analysis_Classification_Output fields."""
    data = assert_analysis_classification_artifact_exists_and_valid_json(path)
    required = [
        "phase",
        "status",
        "analysis_classification_id",
        "request_id",
        "request_kind",
        "source_phase",
        "source_status",
        "snapshot_fingerprint",
        "scan_fingerprint",
        "target_root",
        "detected_source_count",
        "normalized_item_count",
        "classification_count",
        "actionable_count",
        "non_actionable_count",
        "needs_review_count",
        "duplicate_group_count",
        "drift_group_count",
        "items",
        "decisions",
        "groups",
        "notices",
        "classified_source_ids",
        "unclassified_source_ids",
        "duplicate_source_ids",
        "coverage_complete",
        "classification_complete",
        "user_choice_required",
        "dossier_evidence_refs",
        "next_route",
        "analysis_classification_fingerprint",
        "metadata",
    ]
    for field in required:
        assert field in data, f"Missing required field: {field}"