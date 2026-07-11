"""
Duplicate and drift grouping.

Builds Classification_Group records from Scan evidence without removing
or hiding individual source records.
"""
import hashlib
import json
from typing import Any

from backend.phases.analysis_classification.schema import (
    Analysis_Item,
    Classification_Decision,
    Classification_Group,
)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _derive_group_id(group_type: str, member_ids: list[str]) -> str:
    payload = {
        "group_type": group_type,
        "member_ids": sorted(member_ids),
    }
    canonical = _canonical_json(payload)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"grp:{digest[:16]}"


def build_groups(
    items: list[Analysis_Item],
    decisions: list[Classification_Decision],
) -> list[Classification_Group]:
    """Build duplicate and drift groups from Scan evidence.

    Args:
        items: Normalized Analysis_Items.
        decisions: Classification decisions (used for cross-referencing only).

    Returns:
        Sorted list of Classification_Group instances.
    """
    groups: list[Classification_Group] = []

    duplicate_items = [item for item in items if item.source_kind == "duplicate_group"]
    for dup in duplicate_items:
        payload = dup.source_payload
        member_paths = payload.get("member_paths", []) or []
        # Map member paths back to source item ids where possible.
        member_ids: list[str] = []
        for path in member_paths:
            matches = [
                item.source_item_id
                for item in items
                if item.source_path == path and item.source_item_id != dup.source_item_id
            ]
            member_ids.extend(matches)
        # Always include the duplicate group item itself.
        if dup.source_item_id not in member_ids:
            member_ids.append(dup.source_item_id)
        member_ids = sorted(set(member_ids))
        group_id = _derive_group_id(payload.get("group_type", "duplicate_implementation"), member_ids)
        groups.append(
            Classification_Group(
                group_id=group_id,
                group_type=payload.get("group_type", "duplicate_implementation"),
                member_source_item_ids=member_ids,
                canonical_candidate_ids=sorted(member_paths),
                evidence_refs=[dup.source_fingerprint],
                recommended_action="needs_review",
            )
        )

    drift_items = [item for item in items if item.source_kind == "drift_record"]
    for drift in drift_items:
        payload = drift.source_payload
        affected_path = payload.get("affected_path")
        reference_path = payload.get("reference_path")
        member_ids = [drift.source_item_id]
        if affected_path:
            matches = [
                item.source_item_id
                for item in items
                if item.source_path == affected_path and item.source_item_id != drift.source_item_id
            ]
            member_ids.extend(matches)
        if reference_path:
            matches = [
                item.source_item_id
                for item in items
                if item.source_path == reference_path and item.source_item_id not in member_ids
            ]
            member_ids.extend(matches)
        member_ids = sorted(set(member_ids))
        group_type = payload.get("drift_type", "artifact_drift")
        group_id = _derive_group_id(group_type, member_ids)
        groups.append(
            Classification_Group(
                group_id=group_id,
                group_type=group_type,
                member_source_item_ids=member_ids,
                canonical_candidate_ids=sorted([p for p in [affected_path, reference_path] if p]),
                evidence_refs=[drift.source_fingerprint],
                recommended_action="needs_review",
            )
        )

    # Sort groups deterministically
    groups.sort(key=lambda g: (g.group_type, g.group_id))
    return groups