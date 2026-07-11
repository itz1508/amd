"""Mutation boundary tests for Inspection phase."""
import pytest

from backend.phases.inspection import run_inspection
from tests.case_builder.assertions import assert_failed_inspection
from tests.case_builder.simulation_output_builder import SimulationOutputBuilder


class TestInspectionMutationBoundary:
    """Inspection must verify mutation-boundary consistency."""

    def test_changed_file_outside_isolated_target_fails(self, tmp_path):
        inp = (
            SimulationOutputBuilder()
            .with_changed_files(["real_target/src/module.py"])
            .with_target_mutations([{"relative_path": "real_target/src/module.py", "operation": "modify"}])
            .with_verification_results([{"relative_path": "real_target/src/module.py", "status": "success"}])
            .build()
        )
        result = run_inspection(inp, tmp_path)
        assert_failed_inspection(result, ["F-SE10", "F-SE11"])

    def test_changed_files_match_target_mutations(self, tmp_path):
        inp = (
            SimulationOutputBuilder()
            .with_changed_files(["isolated_target/src/other.py"])
            .build()
        )
        result = run_inspection(inp, tmp_path)
        assert_failed_inspection(result, ["F-SE12"])

    def test_mutation_boundary_present_before_mutations(self, tmp_path):
        inp = (
            SimulationOutputBuilder()
            .with_apply_mutation_boundary({"boundary_enforced": True})
            .build()
        )
        result = run_inspection(inp, tmp_path)
        assert_failed_inspection(result, ["F-SE09", "F-SE10", "F-SE11"])