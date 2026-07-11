"""
Generic assertions for deterministic phase behavior.

These helpers accept phase-specific field configuration to avoid hardcoding
fields belonging to any single phase.
"""
from typing import Any, Protocol


class HasPhaseOutput(Protocol):
    """Protocol for phase output objects that have to_dict() method."""
    
    def to_dict(self) -> dict[str, Any]: ...


def assert_outputs_deterministic(
    first: HasPhaseOutput,
    second: HasPhaseOutput,
    id_field: str,
    fingerprint_field: str,
    collection_fields: dict[str, str],
) -> None:
    """Assert that two outputs from identical input are identical where required.
    
    Args:
        first: First phase output object
        second: Second phase output object
        id_field: Name of the ID field (e.g., 'analysis_classification_id')
        fingerprint_field: Name of the fingerprint field (e.g., 'analysis_classification_fingerprint')
        collection_fields: Dict mapping collection names to their ID attribute names
            Example: {'items': 'source_item_id', 'decisions': 'classification_id', 'groups': 'group_id'}
    """
    # Check ID fields
    assert getattr(first, id_field) == getattr(second, id_field), \
        f"{id_field} mismatch"
    
    # Check fingerprint fields
    assert getattr(first, fingerprint_field) == getattr(second, fingerprint_field), \
        f"{fingerprint_field} mismatch"
    
    # Check collection fields
    for collection_name, id_attr in collection_fields.items():
        first_ids = [getattr(item, id_attr) for item in getattr(first, collection_name)]
        second_ids = [getattr(item, id_attr) for item in getattr(second, collection_name)]
        assert first_ids == second_ids, f"{collection_name} {id_attr} mismatch"
    
    # Check full serialization
    assert first.to_dict() == second.to_dict()