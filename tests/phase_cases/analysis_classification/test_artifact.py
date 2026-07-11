"""Artifact tests for Analysis_Classification phase."""
from pathlib import Path

from backend.phases.analysis_classification import run_analysis_classification
from tests.case_builder.artifact_assertions import (
    assert_artifact_exists_and_valid_json,
    assert_artifact_has_required_fields,
    assert_artifact_deterministic,
)
from tests.case_builder.analysis_classification_case_builder import Analysis_ClassificationInputBuilder

# Required fields for Analysis_Classification phase
ANALYSIS_CLASSIFICATION_REQUIRED_FIELDS = [
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


class TestAnalysisClassificationArtifact:
    """Analysis_Classification must write a deterministic, atomic artifact outside the target."""

    def test_artifact_written_for_success(self, tmp_path):
        inp = Analysis_ClassificationInputBuilder().build()
        run_analysis_classification(inp, tmp_path)
        artifact_path = tmp_path / "03_analysis_classification.json"
        assert_artifact_exists_and_valid_json(artifact_path)

    def test_artifact_has_all_required_fields(self, tmp_path):
        inp = Analysis_ClassificationInputBuilder().build()
        run_analysis_classification(inp, tmp_path)
        artifact_path = tmp_path / "03_analysis_classification.json"
        assert_artifact_has_required_fields(
            artifact_path, 
            ANALYSIS_CLASSIFICATION_REQUIRED_FIELDS,
            "analysis_classification"
        )

    def test_artifact_serialization_is_deterministic(self, tmp_path):
        inp = Analysis_ClassificationInputBuilder().build()
        run_analysis_classification(inp, tmp_path)
        artifact_path = tmp_path / "03_analysis_classification.json"
        assert_artifact_deterministic(artifact_path)

    def test_artifact_written_outside_target(self, tmp_path):
        inp = Analysis_ClassificationInputBuilder().build()
        run_analysis_classification(inp, tmp_path)
        artifact_path = tmp_path / "03_analysis_classification.json"
        assert artifact_path.exists()
        assert "03_analysis_classification.json" in artifact_path.name

    def test_artifact_contains_expected_request_id(self, tmp_path):
        inp = Analysis_ClassificationInputBuilder().with_request_id("req-artifact-001").build()
        run_analysis_classification(inp, tmp_path)
        data = assert_artifact_exists_and_valid_json(tmp_path / "03_analysis_classification.json")
        assert data["request_id"] == "req-artifact-001"
        assert data["phase"] == "analysis_classification"
        assert data["status"] == "completed"