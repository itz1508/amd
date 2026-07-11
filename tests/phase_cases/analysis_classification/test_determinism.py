"""Determinism tests for Analysis_Classification phase."""
from backend.phases.analysis_classification import run_analysis_classification
from tests.case_builder.determinism_assertions import assert_outputs_deterministic
from tests.case_builder.analysis_classification_case_builder import Analysis_ClassificationInputBuilder
from tests.case_builder.scan_output_builder import ScanOutputBuilder

# Configuration for Analysis_Classification determinism assertions
ANALYSIS_CLASSIFICATION_DETERMINISM_CONFIG = {
    "id_field": "analysis_classification_id",
    "fingerprint_field": "analysis_classification_fingerprint",
    "collection_fields": {
        "items": "source_item_id",
        "decisions": "classification_id", 
        "groups": "group_id",
    },
}


class TestAnalysisClassificationDeterminism:
    """Analysis_Classification must produce deterministic outputs for identical canonical input."""

    def test_identical_input_produces_identical_fingerprint(self, tmp_path):
        inp = Analysis_ClassificationInputBuilder().build()
        result1 = run_analysis_classification(inp, tmp_path)
        result2 = run_analysis_classification(inp, tmp_path)
        assert_outputs_deterministic(result1, result2, **ANALYSIS_CLASSIFICATION_DETERMINISM_CONFIG)

    def test_determinism_with_duplicate_and_drift(self, tmp_path):
        inp = (
            Analysis_ClassificationInputBuilder()
            .with_duplicate_groups([
                {
                    "group_type": "duplicate_implementation",
                    "member_paths": ["isolated_target/src/a.py"],
                    "representative_path": "isolated_target/src/a.py",
                },
            ])
            .with_drift_records([
                {
                    "drift_type": "interface_drift",
                    "affected_path": "isolated_target/src/b.py",
                    "reference_path": "isolated_target/src/c.py",
                },
            ])
            .build()
        )
        result1 = run_analysis_classification(inp, tmp_path)
        result2 = run_analysis_classification(inp, tmp_path)
        assert_outputs_deterministic(result1, result2, **ANALYSIS_CLASSIFICATION_DETERMINISM_CONFIG)

    def test_artifact_is_deterministic(self, tmp_path):
        inp = Analysis_ClassificationInputBuilder().build()
        run_analysis_classification(inp, tmp_path)
        run_analysis_classification(inp, tmp_path)
        from tests.case_builder.artifact_assertions import assert_artifact_deterministic
        assert_artifact_deterministic(tmp_path / "03_analysis_classification.json")