"""
Shared assertions for Analysis_Classification outputs.
"""
from backend.phases.analysis_classification.schema import Analysis_Classification_Output


def assert_successful_classification(result: Analysis_Classification_Output) -> None:
    """Assert that the result represents a successful classification."""
    assert result.phase == "analysis_classification"
    assert result.status == "completed"
    assert result.source_phase == "scan"
    assert result.source_status == "completed"
    assert result.coverage_complete is True
    assert result.classification_complete is True
    assert result.next_route == "statement_output"
    assert result.detected_source_count == result.normalized_item_count
    assert result.normalized_item_count == result.classification_count
    assert result.unclassified_source_ids == []
    assert len(result.decisions) == result.classification_count


def assert_classification_counts_consistent(result: Analysis_Classification_Output) -> None:
    """Assert that decision counts are internally consistent."""
    assert result.actionable_count + result.non_actionable_count == result.classification_count
    assert result.needs_review_count <= result.actionable_count
    assert result.duplicate_group_count == sum(
        1 for g in result.groups if g.group_type.startswith("duplicate_")
    )
    assert result.drift_group_count == sum(
        1 for g in result.groups if g.group_type.endswith("_drift")
    )