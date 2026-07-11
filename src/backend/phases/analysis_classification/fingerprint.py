"""
Deterministic fingerprinting for Analysis_Classification.
"""
import hashlib
import json
from typing import Any

from backend.phases.analysis_classification.schema import (
    Analysis_Classification_Output,
    Analysis_Item,
    Classification_Decision,
    Classification_Group,
    Classification_Notice,
)


def _canonical_json(value: Any) -> str:
    """Return a deterministic JSON serialization for hashing."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _item_fingerprint(item: Analysis_Item) -> dict[str, Any]:
    return {
        "source_item_id": item.source_item_id,
        "source_kind": item.source_kind,
        "source_path": item.source_path,
        "source_fingerprint": item.source_fingerprint,
    }


def _decision_fingerprint(decision: Classification_Decision) -> dict[str, Any]:
    return {
        "classification_id": decision.classification_id,
        "source_item_id": decision.source_item_id,
        "request_kind": decision.request_kind,
        "classification_category": decision.classification_category,
        "actionable": decision.actionable,
        "severity": decision.severity,
        "recommended_action": decision.recommended_action,
        "duplicate_group_id": decision.duplicate_group_id,
        "drift_detected": decision.drift_detected,
    }


def _group_fingerprint(group: Classification_Group) -> dict[str, Any]:
    return {
        "group_id": group.group_id,
        "group_type": group.group_type,
        "member_source_item_ids": sorted(group.member_source_item_ids),
        "canonical_candidate_ids": sorted(group.canonical_candidate_ids),
        "recommended_action": group.recommended_action,
    }


def _notice_fingerprint(notice: Classification_Notice) -> dict[str, Any]:
    return {
        "notice_code": notice.notice_code,
        "severity": notice.severity,
        "source_item_ids": sorted(notice.source_item_ids),
    }


def compute_analysis_classification_id(
    request_id: str,
    request_kind: str,
    scan_fingerprint: str,
) -> str:
    """Compute deterministic analysis_classification_id."""
    payload = {
        "request_id": request_id,
        "request_kind": request_kind,
        "scan_fingerprint": scan_fingerprint,
    }
    canonical = _canonical_json(payload)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"ac:{digest[:16]}"


def compute_analysis_classification_fingerprint(output: Analysis_Classification_Output) -> str:
    """Compute deterministic fingerprint for the complete output."""
    payload = {
        "analysis_classification_id": output.analysis_classification_id,
        "request_id": output.request_id,
        "request_kind": output.request_kind,
        "source_phase": output.source_phase,
        "source_status": output.source_status,
        "snapshot_fingerprint": output.snapshot_fingerprint,
        "scan_fingerprint": output.scan_fingerprint,
        "target_root": output.target_root,
        "items": sorted(
            [_item_fingerprint(i) for i in output.items],
            key=lambda x: (x["source_kind"], x["source_path"] or "", x["source_item_id"]),
        ),
        "decisions": sorted(
            [_decision_fingerprint(d) for d in output.decisions],
            key=lambda x: (x["source_item_id"], x["classification_id"]),
        ),
        "groups": sorted(
            [_group_fingerprint(g) for g in output.groups],
            key=lambda x: (x["group_type"], x["group_id"]),
        ),
        "notices": sorted(
            [_notice_fingerprint(n) for n in output.notices],
            key=lambda x: (x["notice_code"], x["source_item_ids"]),
        ),
        "classified_source_ids": sorted(output.classified_source_ids),
        "unclassified_source_ids": sorted(output.unclassified_source_ids),
        "duplicate_source_ids": sorted(output.duplicate_source_ids),
        "coverage_complete": output.coverage_complete,
        "classification_complete": output.classification_complete,
        "user_choice_required": output.user_choice_required,
        "next_route": output.next_route,
    }
    canonical = _canonical_json(payload)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()