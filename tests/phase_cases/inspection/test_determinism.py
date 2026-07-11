"""Determinism tests for Inspection phase."""
from backend.phases.inspection import run_inspection
from tests.phase_cases.inspection.inspection_determinism_assertions import assert_inspection_outputs_deterministic
from tests.case_builder.simulation_output_builder import SimulationOutputBuilder


class TestInspectionDeterminism:
    """Inspection must produce deterministic outputs for identical canonical input."""

    def test_identical_input_produces_identical_fingerprint(self, tmp_path):
        inp = SimulationOutputBuilder().build()
        result1 = run_inspection(inp, tmp_path)
        result2 = run_inspection(inp, tmp_path)
        assert_inspection_outputs_deterministic(result1, result2)

    def test_failure_reason_ordering_is_deterministic(self, tmp_path):
        inp = (
            SimulationOutputBuilder()
            .with_self_contained_demo({"ran_successfully": False})
            .with_execution_result({"status": "failure", "execution_id": "exec-bad"})
            .with_changed_files(["real_target/src/module.py"])
            .with_target_mutations([{"relative_path": "real_target/src/module.py", "operation": "modify"}])
            .with_verification_results([{"relative_path": "real_target/src/module.py", "status": "success"}])
            .build()
        )
        result1 = run_inspection(inp, tmp_path)
        result2 = run_inspection(inp, tmp_path)
        assert result1.failure_reasons == result2.failure_reasons
