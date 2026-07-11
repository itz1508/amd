"""Assertions for deterministic Analysis_Classification behavior."""

def assert_analysis_classification_outputs_deterministic(first, second) -> None:
    """Assert that two Analysis_Classification outputs from identical input are identical where required."""
    assert first.analysis_classification_id == second.analysis_classification_id
    assert first.analysis_classification_fingerprint == second.analysis_classification_fingerprint
    assert [i.source_item_id for i in first.items] == [i.source_item_id for i in second.items]
    assert [d.classification_id for d in first.decisions] == [d.classification_id for d in second.decisions]
    assert [g.group_id for g in first.groups] == [g.group_id for g in second.groups]
    assert first.to_dict() == second.to_dict()