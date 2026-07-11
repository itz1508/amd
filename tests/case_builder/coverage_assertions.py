"""
Coverage assertions for Analysis_Classification outputs.
"""
from backend.phases.analysis_classification.schema import Analysis_Classification_Output


def assert_complete_coverage(result: Analysis_Classification_Output) -> None:
    """Assert that every detected source record is classified."""
    assert result.coverage_complete is True
    assert result.unclassified_source_ids == []
    assert result.detected_source_count == result.normalized_item_count
    assert result.normalized_item_count == result.classification_count
    assert sorted(result.classified_source_ids) == sorted(
        item.source_item_id for item in result.items
    )
    assert all(
        any(d.source_item_id == item.source_item_id for d in result.decisions)
        for item in result.items
    )


def assert_no_invented_sources(result: Analysis_Classification_Output) -> None:
    """Assert that the phase did not invent source records not in Scan output."""
    scan_source_ids = {item.source_item_id for item in result.items}
    decision_source_ids = {d.source_item_id for d in result.decisions}
    assert decision_source_ids <= scan_source_ids, "Decisions reference unknown source ids"