"""Coverage tests for Analysis_Classification phase."""
from backend.phases.analysis_classification import run_analysis_classification
from tests.case_builder.analysis_classification_case_builder import Analysis_ClassificationInputBuilder
from tests.case_builder.scan_output_builder import ScanOutputBuilder
from tests.case_builder.coverage_assertions import (
    assert_complete_coverage,
    assert_no_invented_sources,
)


class TestCoverage:
    """Coverage invariants must hold for all valid Scan outputs."""

    def test_coverage_complete_for_default_scan(self, tmp_path):
        inp = Analysis_ClassificationInputBuilder().build()
        result = run_analysis_classification(inp, tmp_path)
        assert_complete_coverage(result)

    def test_no_invented_sources(self, tmp_path):
        inp = Analysis_ClassificationInputBuilder().build()
        result = run_analysis_classification(inp, tmp_path)
        assert_no_invented_sources(result)

    def test_coverage_complete_with_notices(self, tmp_path):
        scan = (
            ScanOutputBuilder()
            .with_notices([
                {
                    "notice_code": "unreadable",
                    "relative_path": "bad.py",
                    "reason": "permission denied",
                },
            ])
            .build()
        )
        inp = Analysis_ClassificationInputBuilder().with_scan_output(scan).build()
        result = run_analysis_classification(inp, tmp_path)
        assert result.coverage_complete is True
        assert result.unclassified_source_ids == []
        assert result.detected_source_count == result.classification_count

    def test_coverage_complete_with_duplicate_and_drift(self, tmp_path):
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
        result = run_analysis_classification(inp, tmp_path)
        assert result.coverage_complete is True
        assert result.unclassified_source_ids == []
        assert result.detected_source_count == result.classification_count
