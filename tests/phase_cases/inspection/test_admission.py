"""Admission tests for Inspection phase."""
import pytest

from backend.phases.inspection import run_inspection, InspectionAdmissionError
from tests.case_builder.inspection_case_builder import admission_rejected_cases
from tests.case_builder.simulation_output_builder import SimulationOutputBuilder


class TestInspectionAdmission:
    """Inspection must reject invalid Simulation_Environment outputs at admission."""

    @pytest.mark.parametrize("name, inp, expected_in_message", admission_rejected_cases())
    def test_admission_rejects_invalid_input(self, name, inp, expected_in_message, tmp_path):
        with pytest.raises(InspectionAdmissionError, match=expected_in_message):
            run_inspection(inp, tmp_path)

    def test_valid_simulation_output_passes_admission(self, tmp_path):
        inp = SimulationOutputBuilder().build()
        result = run_inspection(inp, tmp_path)
        assert result.phase == "inspection"
        assert result.status == "completed"
        assert result.inspection_passed is True