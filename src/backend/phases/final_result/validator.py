"""Final_Result validation functions."""
from typing import Any
from .schema import (
    Final_Result_Input,
    SUPPORTED_TERMINAL_STATES,
    TERMINAL_STATE_STATUS,
)
from .errors import (
    MissingSourcePhaseError,
    MissingSourceFingerprintError,
    UnsupportedTerminalStateError,
    ContradictoryStatusError,
    MissingFailureReasonsError,
    ContradictoryRouteHistoryError,
    MalformedEvidenceReferencesError,
    InvalidCleanupRequestError,
)


def validate_final_result_input(input_data: Final_Result_Input) -> None:
    """Validate Final_Result input.
    
    Reject input when:
    - source phase is missing
    - source fingerprint is missing
    - terminal state is unsupported
    - source status contradicts terminal state
    - failed result has no failure reason
    - route history contradicts source phase
    - evidence references are malformed
    - cleanup request is not boolean
    """
    # Check source phase
    if not input_data.source_phase:
        raise MissingSourcePhaseError("source_phase is missing")
    
    # Check source fingerprint
    if not input_data.source_fingerprint:
        raise MissingSourceFingerprintError("source_fingerprint is missing")
    
    # Check terminal state
    if input_data.terminal_state not in SUPPORTED_TERMINAL_STATES:
        raise UnsupportedTerminalStateError(
            f"Unsupported terminal state: {input_data.terminal_state}. "
            f"Supported: {sorted(SUPPORTED_TERMINAL_STATES)}"
        )
    
    # Check status contradicts terminal state
    expected_status = TERMINAL_STATE_STATUS.get(input_data.terminal_state, "failed")
    if input_data.source_status != expected_status:
        raise ContradictoryStatusError(
            f"source_status '{input_data.source_status}' contradicts "
            f"terminal_state '{input_data.terminal_state}'. Expected: {expected_status}"
        )
    
    # Check failed result has failure reasons
    if input_data.terminal_state != "completed" and not input_data.failure_reasons:
        raise MissingFailureReasonsError(
            f"Failed terminal state '{input_data.terminal_state}' requires failure_reasons"
        )
    
    # Check route history consistency
    validate_route_history_consistency(input_data)
    
    # Check evidence references are not malformed
    for ref in input_data.dossier_evidence_refs:
        if not isinstance(ref, str) or not ref.strip():
            raise MalformedEvidenceReferencesError(f"Malformed evidence reference: {ref}")
    
    # Check cleanup request is boolean
    if not isinstance(input_data.cleanup_requested, bool):
        raise InvalidCleanupRequestError(f"cleanup_requested must be boolean, got {type(input_data.cleanup_requested)}")


def validate_route_history_consistency(input_data: Final_Result_Input) -> None:
    """Validate that route history is consistent with source phase."""
    route_history = input_data.route_history
    source_phase = input_data.source_phase
    
    if not route_history:
        return
    
    # Check that the source phase appears in the route history
    phases_in_history = [r.get("phase", "") for r in route_history if isinstance(r, dict)]
    if source_phase not in phases_in_history:
        raise ContradictoryRouteHistoryError(
            f"Source phase '{source_phase}' not found in route history: {phases_in_history}"
        )
    
    # Check that successful terminal states with inspection source end with Inspection-to-Final_Result
    # Only apply this check for completed terminal state, not failed states
    if (source_phase == "inspection" and 
        input_data.terminal_state == "completed" and
        route_history and 
        len(route_history) > 0):
        last_route = route_history[-1]
        if isinstance(last_route, dict):
            if (last_route.get("phase") == "inspection" and 
                last_route.get("next_route") != "final_result"):
                raise ContradictoryRouteHistoryError(
                    f"Successful inspection route must end with Inspection-to-Final_Result, "
                    f"got: {last_route}"
                )


def validate_evidence_references(dossier_evidence_refs: list[str]) -> None:
    """Validate evidence references are well-formed."""
    for ref in dossier_evidence_refs:
        if not isinstance(ref, str) or not ref.strip():
            raise MalformedEvidenceReferencesError(f"Malformed evidence reference: {ref}")