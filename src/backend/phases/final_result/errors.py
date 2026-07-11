"""Final_Result error hierarchy."""


class FinalResultError(Exception):
    """Base error for Final_Result phase."""
    pass


class ValidationError(FinalResultError):
    """Validation failed for Final_Result input."""
    pass


class MissingSourcePhaseError(ValidationError):
    """Source phase is missing from input."""
    pass


class MissingSourceFingerprintError(ValidationError):
    """Source fingerprint is missing from input."""
    pass


class UnsupportedTerminalStateError(ValidationError):
    """Terminal state is not supported."""
    pass


class ContradictoryStatusError(ValidationError):
    """Source status contradicts terminal state."""
    pass


class MissingFailureReasonsError(ValidationError):
    """Failed result has no failure reasons."""
    pass


class ContradictoryRouteHistoryError(ValidationError):
    """Route history contradicts source phase."""
    pass


class MalformedEvidenceReferencesError(ValidationError):
    """Evidence references are malformed."""
    pass


class InvalidCleanupRequestError(ValidationError):
    """Cleanup request is not boolean."""
    pass


class LockError(FinalResultError):
    """Locking-related errors."""
    pass


class AlreadyLockedError(LockError):
    """Result is already locked and cannot be modified."""
    pass


class IdempotentMismatchError(LockError):
    """Different content using same final_result_id."""
    pass