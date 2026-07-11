"""Admission tests for Analysis_Classification phase."""
import pytest

from backend.phases.analysis_classification import (
    run_analysis_classification,
    Analysis_Classification_Admission_Error,
)
from tests.case_builder.analysis_classification_case_builder import (
    admission_rejected_cases,
    Analysis_ClassificationInputBuilder,
)


class TestAnalysisClassificationAdmission:
    """Analysis_Classification must reject structurally invalid Scan input at admission."""

    @pytest.mark.parametrize("name, inp, expected_in_message", admission_rejected_cases())
    def test_admission_rejects_invalid_input(self, name, inp, expected_in_message, tmp_path):
        with pytest.raises(Analysis_Classification_Admission_Error, match=expected_in_message):
            run_analysis_classification(inp, tmp_path)

    def test_valid_scan_output_passes_admission(self, tmp_path):
        inp = Analysis_ClassificationInputBuilder().build()
        result = run_analysis_classification(inp, tmp_path)
        assert result.phase == "analysis_classification"
        assert result.status == "completed"
        assert result.source_phase == "scan"
        assert result.source_status == "completed"

    def test_dict_input_accepted(self, tmp_path):
        inp = Analysis_ClassificationInputBuilder().build_dict()
        result = run_analysis_classification(inp, tmp_path)
        assert result.request_id == "req-001"
        assert result.status == "completed"