"""Gap Evaluation schema definitions."""
from dataclasses import dataclass, field
from typing import Any
from enum import Enum


class Gap_Status(str, Enum):
    """Gap status enumerations."""
    detected = "detected"
    resolved = "resolved"
    unresolved = "unresolved"


class Gap_Severity(str, Enum):
    """Gap severity enumerations."""
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class Evaluation_Status(str, Enum):
    """Evaluation status enumerations."""
    valid = "valid"
    not_valid = "not_valid"
    pending = "pending"


class Next_Route(str, Enum):
    """Next route enumerations."""
    simulation_environment = "simulation_environment"
    gap_handoff = "gap_handoff"


@dataclass
class Gap_Item:
    """Single gap detected during evaluation.
    
    Contains all required fields:
    - gap_code: Unique identifier for gap type
    - affected_item: Identifier of affected item
    - evidence: Evidence supporting the gap detection
    - failure_reason: Reason for the failure/gap
    - required_patch: Description of required patch
    - success_looks_like: Description of success condition
    """
    gap_code: str
    affected_item: str
    evidence: str
    failure_reason: str
    required_patch: str
    success_looks_like: str
    severity: Gap_Severity = Gap_Severity.medium
    status: Gap_Status = Gap_Status.detected
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "gap_code": self.gap_code,
            "affected_item": self.affected_item,
            "evidence": self.evidence,
            "failure_reason": self.failure_reason,
            "required_patch": self.required_patch,
            "success_looks_like": self.success_looks_like,
            "severity": self.severity.value,
            "status": self.status.value,
            "metadata": dict(self.metadata),
        }


@dataclass
class Package_Plan_Patch:
    """Patch to apply to package plan.
    
    Represents a compatible correction to be applied together with other patches.
    Each applied patch records:
    - patch_id
    - affected_item
    - original_value
    - corrected_value
    - evidence
    - related_gap_codes
    """
    patch_id: str
    target_field: str
    current_value: Any
    new_value: Any
    affected_item: str
    original_value: Any
    corrected_value: Any
    evidence: str
    related_gap_codes: list[str] = field(default_factory=list)
    patch_type: str = "replace"
    compatible_with: list[str] = field(default_factory=list)
    incompatible_with: list[str] = field(default_factory=list)
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "patch_id": self.patch_id,
            "target_field": self.target_field,
            "current_value": self.current_value,
            "new_value": self.new_value,
            "affected_item": self.affected_item,
            "original_value": self.original_value,
            "corrected_value": self.corrected_value,
            "evidence": self.evidence,
            "related_gap_codes": list(self.related_gap_codes),
            "patch_type": self.patch_type,
            "compatible_with": list(self.compatible_with),
            "incompatible_with": list(self.incompatible_with),
            "description": self.description,
            "metadata": dict(self.metadata),
        }
    
    def is_compatible_with(self, other_patch_ids: list[str]) -> bool:
        """Check if this patch is compatible with given patch IDs."""
        for other_id in other_patch_ids:
            if other_id in self.incompatible_with:
                return False
        return True


@dataclass
class Gap_Evaluation_Attempt:
    """Single evaluation attempt record."""
    attempt_number: int
    status: Evaluation_Status
    gaps: list[Gap_Item] = field(default_factory=list)
    applied_patches: list[Package_Plan_Patch] = field(default_factory=list)
    readiness: float = 0.0
    required_grader_failures: list[str] = field(default_factory=list)
    unresolved_conflict: bool = False
    simulation_ready: bool = False
    timestamp: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "attempt_number": self.attempt_number,
            "status": self.status.value,
            "gaps": [g.to_dict() for g in self.gaps],
            "applied_patches": [p.to_dict() for p in self.applied_patches],
            "readiness": self.readiness,
            "required_grader_failures": list(self.required_grader_failures),
            "unresolved_conflict": self.unresolved_conflict,
            "simulation_ready": self.simulation_ready,
            "timestamp": self.timestamp,
            "metadata": dict(self.metadata),
        }


@dataclass
class Gap_Evaluation_Input:
    """Input boundary for Gap_Evaluation phase.
    
    Consumes:
    - Statement_Output_Output
    - package plan
    - supporting metadata
    - dossier evidence references
    """
    statement_output: dict[str, Any]
    package_plan: dict[str, Any]
    supporting_metadata: dict[str, Any] = field(default_factory=dict)
    dossier_evidence_refs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "statement_output": dict(self.statement_output),
            "package_plan": dict(self.package_plan),
            "supporting_metadata": dict(self.supporting_metadata),
            "dossier_evidence_refs": list(self.dossier_evidence_refs),
        }


@dataclass
class Gap_Evaluation_Output:
    """Final Gap_Evaluation artifact.
    
    Contains:
    - phase, status, readiness, simulation_ready
    - required_grader_failures, unresolved_conflict
    - attempts, gaps, applied_package_plan_patches
    - resulting_package_plan, supporting_metadata, dossier_evidence_refs
    - next_route, handoff_ref, gap_evaluation_fingerprint
    """
    phase: str
    status: str
    readiness: float
    simulation_ready: bool
    required_grader_failures: list[str]
    unresolved_conflict: bool
    attempts: list[Gap_Evaluation_Attempt]
    gaps: list[Gap_Item]
    applied_package_plan_patches: list[Package_Plan_Patch]
    resulting_package_plan: dict[str, Any]
    supporting_metadata: dict[str, Any]
    dossier_evidence_refs: list[str]
    next_route: str
    handoff_ref: str | None = None
    gap_evaluation_fingerprint: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "status": self.status,
            "readiness": self.readiness,
            "simulation_ready": self.simulation_ready,
            "required_grader_failures": list(self.required_grader_failures),
            "unresolved_conflict": self.unresolved_conflict,
            "attempts": [a.to_dict() for a in self.attempts],
            "gaps": [g.to_dict() for g in self.gaps],
            "applied_package_plan_patches": [p.to_dict() for p in self.applied_package_plan_patches],
            "resulting_package_plan": dict(self.resulting_package_plan),
            "supporting_metadata": dict(self.supporting_metadata),
            "dossier_evidence_refs": list(self.dossier_evidence_refs),
            "next_route": self.next_route,
            "handoff_ref": self.handoff_ref,
            "gap_evaluation_fingerprint": self.gap_evaluation_fingerprint,
            "metadata": dict(self.metadata),
        }
