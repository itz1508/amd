"""
Inspection schema definitions.
"""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Inspection_Evidence_Record:
    """A single piece of evidence referenced by an inspection check or finding."""
    evidence_type: str
    evidence_id: str
    source_phase: str
    payload_summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_type": self.evidence_type,
            "evidence_id": self.evidence_id,
            "source_phase": self.source_phase,
            "payload_summary": self.payload_summary,
        }


@dataclass
class Inspection_Check:
    """Result of a single read-only inspection check."""
    check_code: str
    check_name: str
    passed: bool
    evidence_refs: list[Inspection_Evidence_Record] = field(default_factory=list)
    failure_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_code": self.check_code,
            "check_name": self.check_name,
            "passed": self.passed,
            "evidence_refs": [e.to_dict() for e in self.evidence_refs],
            "failure_reason": self.failure_reason,
            "metadata": self.metadata,
        }


@dataclass
class Inspection_Finding:
    """A finding produced when a check fails or an anomaly is detected."""
    finding_code: str
    severity: str
    affected_item: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)
    failure_reason: str | None = None
    success_looks_like: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_code": self.finding_code,
            "severity": self.severity,
            "affected_item": self.affected_item,
            "evidence": self.evidence,
            "failure_reason": self.failure_reason,
            "success_looks_like": self.success_looks_like,
            "metadata": self.metadata,
        }


@dataclass
class Inspection_Input:
    """Frozen Simulation_Environment output consumed by Inspection."""
    phase: str
    status: str
    simulation_environment_id: str
    gap_evaluation_fingerprint: str
    simulation_environment_fingerprint: str
    isolated_environment: dict[str, Any] = field(default_factory=dict)
    self_contained_demo: dict[str, Any] = field(default_factory=dict)
    execution_result: dict[str, Any] = field(default_factory=dict)
    execution_attempt_count: int = 0
    apply_mutation_boundary: dict[str, Any] = field(default_factory=dict)
    target_mutations: list[dict[str, Any]] = field(default_factory=list)
    changed_files: list[str] = field(default_factory=list)
    post_apply_verification: dict[str, Any] = field(default_factory=dict)
    verification_results: list[dict[str, Any]] = field(default_factory=list)
    dossier_evidence_refs: list[dict[str, Any]] = field(default_factory=list)
    unresolved_conflict: bool = False
    regression_detected: bool = False
    real_target_unchanged: bool = True
    next_route: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "status": self.status,
            "simulation_environment_id": self.simulation_environment_id,
            "gap_evaluation_fingerprint": self.gap_evaluation_fingerprint,
            "simulation_environment_fingerprint": self.simulation_environment_fingerprint,
            "isolated_environment": self.isolated_environment,
            "self_contained_demo": self.self_contained_demo,
            "execution_result": self.execution_result,
            "execution_attempt_count": self.execution_attempt_count,
            "apply_mutation_boundary": self.apply_mutation_boundary,
            "target_mutations": self.target_mutations,
            "changed_files": self.changed_files,
            "post_apply_verification": self.post_apply_verification,
            "verification_results": self.verification_results,
            "dossier_evidence_refs": self.dossier_evidence_refs,
            "unresolved_conflict": self.unresolved_conflict,
            "regression_detected": self.regression_detected,
            "real_target_unchanged": self.real_target_unchanged,
            "next_route": self.next_route,
            "metadata": self.metadata,
        }


@dataclass
class Inspection_Output:
    """Inspection phase output."""
    phase: str
    status: str
    terminal_state: str
    inspection_id: str
    source_phase: str
    source_status: str
    source_fingerprint: str
    gap_evaluation_fingerprint: str
    simulation_environment_fingerprint: str
    inspection_passed: bool
    checks: list[Inspection_Check] = field(default_factory=list)
    findings: list[Inspection_Finding] = field(default_factory=list)
    failure_reasons: list[str] = field(default_factory=list)
    dossier_evidence_refs: list[dict[str, Any]] = field(default_factory=list)
    route_history: list[str] = field(default_factory=list)
    real_target_unchanged: bool = True
    unresolved_conflict: bool = False
    regression_detected: bool = False
    next_route: str = "final_result"
    inspection_fingerprint: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "status": self.status,
            "terminal_state": self.terminal_state,
            "inspection_id": self.inspection_id,
            "source_phase": self.source_phase,
            "source_status": self.source_status,
            "source_fingerprint": self.source_fingerprint,
            "gap_evaluation_fingerprint": self.gap_evaluation_fingerprint,
            "simulation_environment_fingerprint": self.simulation_environment_fingerprint,
            "inspection_passed": self.inspection_passed,
            "checks": [c.to_dict() for c in self.checks],
            "findings": [f.to_dict() for f in self.findings],
            "failure_reasons": self.failure_reasons,
            "dossier_evidence_refs": self.dossier_evidence_refs,
            "route_history": self.route_history,
            "real_target_unchanged": self.real_target_unchanged,
            "unresolved_conflict": self.unresolved_conflict,
            "regression_detected": self.regression_detected,
            "next_route": self.next_route,
            "inspection_fingerprint": self.inspection_fingerprint,
            "metadata": self.metadata,
        }