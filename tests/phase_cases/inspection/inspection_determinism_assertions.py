"""Assertions for deterministic Inspection behavior."""

def assert_inspection_outputs_deterministic(first, second) -> None:
    """Assert that two Inspection outputs from identical input are identical where required."""
    assert first.inspection_id == second.inspection_id
    assert first.inspection_fingerprint == second.inspection_fingerprint
    assert [c.check_code for c in first.checks] == [c.check_code for c in second.checks]
    assert [c.passed for c in first.checks] == [c.passed for c in second.checks]
    assert [f.finding_code for f in first.findings] == [f.finding_code for f in second.findings]
    assert first.failure_reasons == second.failure_reasons
    assert first.to_dict() == second.to_dict()