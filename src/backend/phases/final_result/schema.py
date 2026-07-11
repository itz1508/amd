"""Final_Result schema definitions."""
from dataclasses import dataclass, field
from typing import Any
import hashlib
import json


# Supported terminal states
SUPPORTED_TERMINAL_STATES = {
    "completed",
    "failed_gap_evaluation", 
    "failed_simulation_environment",
    "failed_execution",
    "failed_inspection",
}

# Terminal state to status mapping
TERMINAL_STATE_STATUS = {
    "completed": "completed",
    "failed_gap_evaluation": "failed",
    "failed_simulation_environment": "failed", 
    "failed_execution": "failed",
    "failed_inspection": "failed",
}


@dataclass
class Route_Record:
    """Record of a route in the execution history.
    
    Contains:
    - phase: The phase that was routed from
    - next_route: Where it routed to
    - timestamp: When the route occurred (excluded from fingerprint)
    """
    phase: str
    next_route: str
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "next_route": self.next_route,
            "metadata": dict(self.metadata),
        }


@dataclass 
class Terminal_Evidence:
    """Terminal evidence reference."""
    evidence_id: str
    evidence_type: str
    source_phase: str
    location: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "evidence_type": self.evidence_type,
            "source_phase": self.source_phase,
            "location": self.location,
            "metadata": dict(self.metadata),
        }


@dataclass
class Final_Result_Lock:
    """Lock information for Final_Result."""
    final_result_id: str
    lock_fingerprint: str
    locked: bool = False
    locked_at: str = ""  # Timestamp (excluded from fingerprint)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "final_result_id": self.final_result_id,
            "lock_fingerprint": self.lock_fingerprint,
            "locked": self.locked,
            "locked_at": self.locked_at,
        }


@dataclass
class Final_Result_Input:
    """Input boundary for Final_Result phase.
    
    Accepts terminal-route payloads from:
    - Inspection_Output
    - failed Gap_Evaluation escalation  
    - failed Simulation_Environment
    - failed Execution
    - failed Inspection
    """
    source_phase: str
    source_status: str
    source_fingerprint: str
    terminal_state: str
    route_history: list[dict[str, Any]] = field(default_factory=list)
    dossier_evidence_refs: list[str] = field(default_factory=list)
    failure_reasons: list[str] = field(default_factory=list)
    result_summary: str = ""
    cleanup_requested: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "source_phase": self.source_phase,
            "source_status": self.source_status,
            "source_fingerprint": self.source_fingerprint,
            "terminal_state": self.terminal_state,
            "route_history": list(self.route_history),
            "dossier_evidence_refs": list(self.dossier_evidence_refs),
            "failure_reasons": list(self.failure_reasons),
            "result_summary": self.result_summary,
            "cleanup_requested": self.cleanup_requested,
            "metadata": dict(self.metadata),
        }


@dataclass
class Final_Result_Output:
    """Final Final_Result artifact.
    
    Must contain:
    - phase: "final_result"
    - status
    - terminal_state  
    - final_result_id
    - source_phase
    - source_status
    - source_fingerprint
    - route_history
    - dossier_evidence_refs
    - failure_reasons
    - result_summary
    - locked
    - lock_fingerprint
    - cleanup_requested
    - next_route
    - final_result_fingerprint
    """
    phase: str
    status: str
    terminal_state: str
    final_result_id: str
    source_phase: str
    source_status: str
    source_fingerprint: str
    route_history: list[dict[str, Any]]
    dossier_evidence_refs: list[str]
    failure_reasons: list[str]
    result_summary: str
    locked: bool
    lock_fingerprint: str
    cleanup_requested: bool
    next_route: str | None
    final_result_fingerprint: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        result = {
            "phase": self.phase,
            "status": self.status,
            "terminal_state": self.terminal_state,
            "final_result_id": self.final_result_id,
            "source_phase": self.source_phase,
            "source_status": self.source_status,
            "source_fingerprint": self.source_fingerprint,
            "route_history": list(self.route_history),
            "dossier_evidence_refs": list(self.dossier_evidence_refs),
            "failure_reasons": list(self.failure_reasons),
            "result_summary": self.result_summary,
            "locked": self.locked,
            "lock_fingerprint": self.lock_fingerprint,
            "cleanup_requested": self.cleanup_requested,
            "next_route": self.next_route,
            "final_result_fingerprint": self.final_result_fingerprint,
            "metadata": dict(self.metadata),
        }
        return result