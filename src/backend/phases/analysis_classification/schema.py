"""
Analysis_Classification schema definitions.

Uses plain dataclasses to match the existing canonical backend schema style.
"""
from dataclasses import dataclass, field
from typing import Any

from backend.schemas.scan import Scan_Output


@dataclass
class Classification_Evidence:
    """Evidence backing a classification decision."""
    evidence_id: str
    source_item_id: str
    evidence_type: str
    location: str
    content_fingerprint: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "source_item_id": self.source_item_id,
            "evidence_type": self.evidence_type,
            "location": self.location,
            "content_fingerprint": self.content_fingerprint,
            "metadata": self.metadata,
        }


@dataclass
class Analysis_Item:
    """Normalized representation of a single Scan-detected source record."""
    source_item_id: str
    source_kind: str
    source_path: str | None
    source_fingerprint: str
    source_payload: dict[str, Any] = field(default_factory=dict)
    source_evidence_refs: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_item_id": self.source_item_id,
            "source_kind": self.source_kind,
            "source_path": self.source_path,
            "source_fingerprint": self.source_fingerprint,
            "source_payload": self.source_payload,
            "source_evidence_refs": self.source_evidence_refs,
            "metadata": self.metadata,
        }


@dataclass
class Classification_Decision:
    """Classification decision for a single Analysis_Item."""
    classification_id: str
    source_item_id: str
    request_kind: str
    classification_category: str
    actionable: bool
    severity: str
    confidence: float
    recommended_action: str
    allowed_actions: list[str] = field(default_factory=list)
    user_choice_required: bool = False
    rationale: str = ""
    evidence_refs: list[str] = field(default_factory=list)
    affected_paths: list[str] = field(default_factory=list)
    dependency_refs: list[str] = field(default_factory=list)
    duplicate_group_id: str | None = None
    drift_detected: bool = False
    failure_reasons: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "classification_id": self.classification_id,
            "source_item_id": self.source_item_id,
            "request_kind": self.request_kind,
            "classification_category": self.classification_category,
            "actionable": self.actionable,
            "severity": self.severity,
            "confidence": self.confidence,
            "recommended_action": self.recommended_action,
            "allowed_actions": self.allowed_actions,
            "user_choice_required": self.user_choice_required,
            "rationale": self.rationale,
            "evidence_refs": self.evidence_refs,
            "affected_paths": self.affected_paths,
            "dependency_refs": self.dependency_refs,
            "duplicate_group_id": self.duplicate_group_id,
            "drift_detected": self.drift_detected,
            "failure_reasons": self.failure_reasons,
            "metadata": self.metadata,
        }


@dataclass
class Classification_Group:
    """Group of related source items (duplicates or drift)."""
    group_id: str
    group_type: str
    member_source_item_ids: list[str] = field(default_factory=list)
    canonical_candidate_ids: list[str] = field(default_factory=list)
    conflicting_owner_ids: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    recommended_action: str = "needs_review"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "group_id": self.group_id,
            "group_type": self.group_type,
            "member_source_item_ids": self.member_source_item_ids,
            "canonical_candidate_ids": self.canonical_candidate_ids,
            "conflicting_owner_ids": self.conflicting_owner_ids,
            "evidence_refs": self.evidence_refs,
            "recommended_action": self.recommended_action,
            "metadata": self.metadata,
        }


@dataclass
class Classification_Notice:
    """Notice emitted during classification."""
    notice_code: str
    severity: str
    source_item_ids: list[str] = field(default_factory=list)
    message: str = ""
    evidence_refs: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "notice_code": self.notice_code,
            "severity": self.severity,
            "source_item_ids": self.source_item_ids,
            "message": self.message,
            "evidence_refs": self.evidence_refs,
            "metadata": self.metadata,
        }


@dataclass
class Analysis_Classification_Input:
    """Input boundary for Analysis_Classification."""
    request_id: str
    request_text: str
    scan_output: Scan_Output | dict[str, Any]
    request_metadata: dict[str, Any] = field(default_factory=dict)
    dossier_evidence_refs: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        scan_dict: dict[str, Any]
        if isinstance(self.scan_output, Scan_Output):
            scan_dict = self.scan_output.to_dict()
        else:
            scan_dict = dict(self.scan_output)
        return {
            "request_id": self.request_id,
            "request_text": self.request_text,
            "scan_output": scan_dict,
            "request_metadata": self.request_metadata,
            "dossier_evidence_refs": self.dossier_evidence_refs,
            "metadata": self.metadata,
        }


@dataclass
class Analysis_Classification_Output:
    """Output boundary for Analysis_Classification."""
    phase: str
    status: str
    analysis_classification_id: str
    request_id: str
    request_kind: str
    source_phase: str
    source_status: str
    snapshot_fingerprint: str
    scan_fingerprint: str
    target_root: str
    detected_source_count: int
    normalized_item_count: int
    classification_count: int
    actionable_count: int
    non_actionable_count: int
    needs_review_count: int
    duplicate_group_count: int
    drift_group_count: int
    items: list[Analysis_Item] = field(default_factory=list)
    decisions: list[Classification_Decision] = field(default_factory=list)
    groups: list[Classification_Group] = field(default_factory=list)
    notices: list[Classification_Notice] = field(default_factory=list)
    classified_source_ids: list[str] = field(default_factory=list)
    unclassified_source_ids: list[str] = field(default_factory=list)
    duplicate_source_ids: list[str] = field(default_factory=list)
    coverage_complete: bool = False
    classification_complete: bool = False
    user_choice_required: bool = False
    dossier_evidence_refs: list[str] = field(default_factory=list)
    next_route: str = "statement_output"
    analysis_classification_fingerprint: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "status": self.status,
            "analysis_classification_id": self.analysis_classification_id,
            "request_id": self.request_id,
            "request_kind": self.request_kind,
            "source_phase": self.source_phase,
            "source_status": self.source_status,
            "snapshot_fingerprint": self.snapshot_fingerprint,
            "scan_fingerprint": self.scan_fingerprint,
            "target_root": self.target_root,
            "detected_source_count": self.detected_source_count,
            "normalized_item_count": self.normalized_item_count,
            "classification_count": self.classification_count,
            "actionable_count": self.actionable_count,
            "non_actionable_count": self.non_actionable_count,
            "needs_review_count": self.needs_review_count,
            "duplicate_group_count": self.duplicate_group_count,
            "drift_group_count": self.drift_group_count,
            "items": [i.to_dict() for i in self.items],
            "decisions": [d.to_dict() for d in self.decisions],
            "groups": [g.to_dict() for g in self.groups],
            "notices": [n.to_dict() for n in self.notices],
            "classified_source_ids": self.classified_source_ids,
            "unclassified_source_ids": self.unclassified_source_ids,
            "duplicate_source_ids": self.duplicate_source_ids,
            "coverage_complete": self.coverage_complete,
            "classification_complete": self.classification_complete,
            "user_choice_required": self.user_choice_required,
            "dossier_evidence_refs": self.dossier_evidence_refs,
            "next_route": self.next_route,
            "analysis_classification_fingerprint": self.analysis_classification_fingerprint,
            "metadata": self.metadata,
        }