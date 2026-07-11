"""Routing tests for failed Inspection results."""
import pytest

from backend.phases.inspection import run_inspection
from tests.case_builder.assertions import assert_routes_only_to_final_result, assert_failed_inspection
from tests.case_builder.simulation_output_builder import SimulationOutputBuilder


class TestInspectionFailureRoutes:
    """Failed Inspection must route only to final_result with terminal_state failed_inspection."""

    def test_successful_result_routes_to_final_result(self, tmp_path):
        inp = SimulationOutputBuilder().build()
        result = run_inspection(inp, tmp_path)
        assert result.status == "completed"
        assert result.terminal_state == "completed"
        assert_routes_only_to_final_result(result)

    @pytest.mark.parametrize(
        "name, builder_call",
        [
            ("unresolved conflict", lambda b: b.with_unresolved_conflict(True)),
            ("detected regression", lambda b: b.with_regression_detected(True)),
            ("failed verification", lambda b: b.with_post_apply_verification({"status": "failure"})),
        ],
    )
    def test_failed_result_routes_to_final_result(self, name, builder_call, tmp_path):
        inp = builder_call(SimulationOutputBuilder()).build()
        result = run_inspection(inp, tmp_path)
        assert_failed_inspection(result)
        assert_routes_only_to_final_result(result)