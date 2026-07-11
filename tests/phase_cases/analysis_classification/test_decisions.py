"""Classification decision tests for Analysis_Classification phase."""
from backend.phases.analysis_classification import run_analysis_classification
from tests.case_builder.analysis_classification_case_builder import Analysis_ClassificationInputBuilder
from tests.case_builder.scan_output_builder import ScanOutputBuilder
from backend.schemas.scan import Scan_File


class TestClassificationDecisions:
    """Exactly one evidence-backed decision must be produced per Analysis_Item."""

    def test_one_decision_per_item(self, tmp_path):
        inp = Analysis_ClassificationInputBuilder().build()
        result = run_analysis_classification(inp, tmp_path)
        assert len(result.decisions) == len(result.items)
        assert result.classification_count == len(result.items)

    def test_source_file_classified_maintainability(self, tmp_path):
        inp = Analysis_ClassificationInputBuilder().build()
        result = run_analysis_classification(inp, tmp_path)
        module_decision = next(
            d for d in result.decisions
            if d.source_item_id == next(
                i.source_item_id for i in result.items
                if i.source_path == "isolated_target/src/module.py"
            )
        )
        assert module_decision.classification_category == "maintainability"
        assert module_decision.actionable is False

    def test_config_file_classified_no_change(self, tmp_path):
        inp = Analysis_ClassificationInputBuilder().build()
        result = run_analysis_classification(inp, tmp_path)
        config_decision = next(
            d for d in result.decisions
            if d.source_item_id == next(
                i.source_item_id for i in result.items
                if i.source_path == "isolated_target/pyproject.toml"
            )
        )
        assert config_decision.classification_category == "configuration"
        assert config_decision.recommended_action == "no_change"

    def test_test_file_classified_test_gap(self, tmp_path):
        inp = Analysis_ClassificationInputBuilder().build()
        result = run_analysis_classification(inp, tmp_path)
        test_decision = next(
            d for d in result.decisions
            if d.source_item_id == next(
                i.source_item_id for i in result.items
                if i.source_path == "isolated_target/tests/test_module.py"
            )
        )
        assert test_decision.classification_category == "test_gap"

    def test_unsupported_language_needs_review(self, tmp_path):
        scan = (
            ScanOutputBuilder()
            .with_files([
                Scan_File(
                    relative_path="isolated_target/src/legacy.xyz",
                    file_type="source",
                    language=None,
                    size_bytes=50,
                    sha256="sha256-legacy",
                    category="module",
                ),
            ])
            .with_surfaces([])
            .with_notices([])
            .build()
        )
        inp = Analysis_ClassificationInputBuilder().with_scan_output(scan).build()
        result = run_analysis_classification(inp, tmp_path)
        decision = result.decisions[0]
        assert decision.classification_category == "unsupported"
        assert decision.actionable is True
        assert decision.recommended_action == "needs_review"

    def test_decisions_reference_source_evidence(self, tmp_path):
        inp = Analysis_ClassificationInputBuilder().build()
        result = run_analysis_classification(inp, tmp_path)
        for decision in result.decisions:
            assert decision.evidence_refs
            assert all(isinstance(ref, str) and ref for ref in decision.evidence_refs)