"""Gap Evaluation errors."""


class GapEvaluationError(Exception):
    """Base error for Gap Evaluation phase."""
    pass


class InvalidInputError(GapEvaluationError):
    """Raised when input is invalid or missing required fields."""
    pass


class ReadinessThresholdError(GapEvaluationError):
    """Raised when readiness is below threshold."""
    pass


class GraderFailureError(GapEvaluationError):
    """Raised when required grader failures are present."""
    pass


class ConflictError(GapEvaluationError):
    """Raised when unresolved conflicts are present."""
    pass


class SimulationNotReadyError(GapEvaluationError):
    """Raised when simulation_ready is false."""
    pass


class MaxAttemptsExceededError(GapEvaluationError):
    """Raised when attempt count exceeds maximum allowed."""
    pass


class PatchApplicationError(GapEvaluationError):
    """Raised when patch application fails."""
    pass


class IncompatiblePatchError(GapEvaluationError):
    """Raised when incompatible patches are detected."""
    pass
