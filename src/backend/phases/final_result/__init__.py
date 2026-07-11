"""Final_Result phase package."""
from .runner import run_final_result
from .schema import (
    Final_Result_Input,
    Final_Result_Output,
    Route_Record,
    Terminal_Evidence,
    Final_Result_Lock,
    SUPPORTED_TERMINAL_STATES,
    TERMINAL_STATE_STATUS,
)
from .validator import (
    validate_final_result_input,
    validate_route_history_consistency,
    validate_evidence_references,
)
from .locking import (
    compute_lock_fingerprint,
    compute_final_result_id,
    create_lock,
    check_lock,
    acquire_lock,
    is_locked,
    get_lock,
    clear_locks,
    final_result_fingerprint,
)
from .errors import (
    FinalResultError,
    ValidationError,
    MissingSourcePhaseError,
    MissingSourceFingerprintError,
    UnsupportedTerminalStateError,
    ContradictoryStatusError,
    MissingFailureReasonsError,
    ContradictoryRouteHistoryError,
    MalformedEvidenceReferencesError,
    InvalidCleanupRequestError,
    LockError,
    AlreadyLockedError,
    IdempotentMismatchError,
)

__all__ = [
    # Runner
    "run_final_result",
    
    # Schema
    "Final_Result_Input",
    "Final_Result_Output",
    "Route_Record",
    "Terminal_Evidence",
    "Final_Result_Lock",
    "SUPPORTED_TERMINAL_STATES",
    "TERMINAL_STATE_STATUS",
    
    # Validator
    "validate_final_result_input",
    "validate_route_history_consistency",
    "validate_evidence_references",
    
    # Locking
    "compute_lock_fingerprint",
    "compute_final_result_id",
    "create_lock",
    "check_lock",
    "acquire_lock",
    "is_locked",
    "get_lock",
    "clear_locks",
    "final_result_fingerprint",
    
    # Errors
    "FinalResultError",
    "ValidationError",
    "MissingSourcePhaseError",
    "MissingSourceFingerprintError",
    "UnsupportedTerminalStateError",
    "ContradictoryStatusError",
    "MissingFailureReasonsError",
    "ContradictoryRouteHistoryError",
    "MalformedEvidenceReferencesError",
    "InvalidCleanupRequestError",
    "LockError",
    "AlreadyLockedError",
    "IdempotentMismatchError",
]