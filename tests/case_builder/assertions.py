"""
Shared assertions for Inspection outputs.
"""
from backend.phases.inspection.schema import Inspection_Output


def assert_successful_inspection(result: Inspection_Output) -> None:
    """Assert that the result represents a successful inspection."""
    assert result.phase == "inspection"
    assert result.status == "completed"
    assert result.terminal_state == "completed"
    assert result.inspection_passed is True
    assert result.next_route == "final_result"
    assert all(c.passed for c in result.checks)
    assert result.findings == []
    assert result.failure_reasons == []


def assert_failed_inspection(result: Inspection_Output, expected_finding_codes: list[str] | None = None) -> None:
    """Assert that the result represents a failed inspection."""
    assert result.phase == "inspection"
    assert result.status == "failed"
    assert result.terminal_state == "failed_inspection"
    assert result.inspection_passed is False
    assert result.next_route == "final_result"
    assert any(not c.passed for c in result.checks)
    assert result.findings
    assert result.failure_reasons
    if expected_finding_codes:
        actual = {f.finding_code for f in result.findings}
        expected = set(expected_finding_codes)
        assert expected <= actual, f"Expected findings {expected}, got {actual}"


def assert_routes_only_to_final_result(result: Inspection_Output) -> None:
    """Assert that the result routes only to final_result."""
    assert result.next_route == "final_result"
    assert result.next_route not in ("gap_evaluation", "simulation_environment", "execution", "inspection")