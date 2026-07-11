"""Source normalization tests for Analysis_Classification phase."""
from backend.phases.analysis_classification import run_analysis_classification
from backend.phases.analysis_classification.normalizer import normalize_scan_output
from tests.case_builder.analysis_classification_case_builder import Analysis_ClassificationInputBuilder
from tests.case_builder.scan_output_builder import ScanOutputBuilder
from backend.schemas.scan import Scan_File, Scan_Surface, Scan_Notice


class TestSourceNormalization:
    """Every Scan record must become one deterministic Analysis_Item."""

    def test_files_surfaces_notices_all_normalized(self, tmp_path):
        inp = Analysis_ClassificationInputBuilder().build()
        result = run_analysis_classification(inp, tmp_path)
        assert result.detected_source_count == 4  # 3 files + 1 surface
        assert result.normalized_item_count == 4
        assert len(result.items) == 4

    def test_empty_scan_produces_no_items(self, tmp_path):
        scan = (
            ScanOutputBuilder()
            .with_files([])
            .with_surfaces([])
            .with_notices([])
            .build()
        )
        inp = Analysis_ClassificationInputBuilder().with_scan_output(scan).build()
        result = run_analysis_classification(inp, tmp_path)
        assert result.detected_source_count == 0
        assert result.normalized_item_count == 0
        assert result.classification_count == 0

    def test_incomplete_file_record_is_unreadable(self):
        scan = ScanOutputBuilder().with_files([{"relative_path": "x.py"}]).build()
        items = normalize_scan_output(scan)
        assert len(items) == 1
        assert items[0].source_kind == "unreadable"

    def test_incomplete_surface_record_is_unknown(self):
        scan = ScanOutputBuilder().with_surfaces([{"surface_type": "entry_point"}]).build()
        items = normalize_scan_output(scan)
        assert len(items) == 4  # 3 files + 1 unknown surface
        unknown = [i for i in items if i.source_kind == "unknown"]
        assert len(unknown) == 1

    def test_notice_unreadable_becomes_actionable(self, tmp_path):
        scan = (
            ScanOutputBuilder()
            .with_files([])
            .with_surfaces([])
            .with_notices([Scan_Notice(notice_code="unreadable", relative_path="bad.py", reason="permission denied")])
            .build()
        )
        inp = Analysis_ClassificationInputBuilder().with_scan_output(scan).build()
        result = run_analysis_classification(inp, tmp_path)
        notice_decisions = [d for d in result.decisions if d.classification_category == "unreadable"]
        assert len(notice_decisions) == 1
        assert notice_decisions[0].actionable is True
        assert notice_decisions[0].recommended_action == "needs_review"

    def test_source_item_ids_are_deterministic(self):
        scan = ScanOutputBuilder().build()
        first = [i.source_item_id for i in normalize_scan_output(scan)]
        second = [i.source_item_id for i in normalize_scan_output(scan)]
        assert first == second