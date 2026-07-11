"""Evidence check tests for Inspection phase."""
import pytest

from backend.phases.inspection import run_inspection
from tests.case_builder.inspection_case_builder import failed_check_cases
from tests.case_builder.assertions import assert_failed_inspection
from tests.case_builder.simulation_output_builder import SimulationOutputBuilder


class TestInspectionEvidenceChecks:
    """Inspection must return all failed evidence checks together."""

    @pytest.mark.parametrize("name, inp, expected_finding_codes", failed_check_cases())
    def test_failed_checks_returned_together(self, name, inp, expected_finding_codes, tmp_path):
        result = run_inspection(inp, tmp_path)
        assert_failed_inspection(result, expected_finding_codes)

    def test_all_checks_returned_even_after_first_failure(self, tmp_path):
        inp = (
            SimulationOutputBuilder()
            .with_self_contained_demo({"ran_successfully": False})
            .with_execution_result({"status": "failure", "execution_id": "exec-bad"})
            .with_changed_files(["real_target/src/module.py"])
            .with_target_mutations([{"relative_path": "real_target/src/module.py", "operation": "modify"}])
            .with_verification_results([{"relative_path": "real_target/src/module.py", "status": "success"}])
            .build()
        )
        result = run_inspection(inp, tmp_path)
        assert result.status == "failed"
        assert len(result.checks) == 20
        assert len([c for c in result.checks if not c.passed]) >= 3
