"""Simulation Environment errors."""


class SimulationEnvironmentError(Exception):
    """Base error for Simulation Environment phase."""
    pass


class AdmissionError(SimulationEnvironmentError):
    """Raised when admission requirements are not met."""
    pass


class ReadinessThresholdError(AdmissionError):
    """Raised when readiness is below threshold."""
    pass


class SimulationNotReadyError(AdmissionError):
    """Raised when simulation_ready is false."""
    pass


class GraderFailureError(AdmissionError):
    """Raised when required grader failures are present."""
    pass


class ConflictError(AdmissionError):
    """Raised when unresolved conflicts are present."""
    pass


class WrongRouteError(AdmissionError):
    """Raised when next_route is not simulation_environment."""
    pass


class PackagePlanFingerprintMismatchError(AdmissionError):
    """Raised when package plan fingerprint doesn't match."""
    pass


class EnvironmentPreparationError(SimulationEnvironmentError):
    """Raised when isolated environment cannot be prepared."""
    pass


class MissingDemoDependencyError(EnvironmentPreparationError):
    """Raised when demo has missing dependencies."""
    pass


class IsolationError(SimulationEnvironmentError):
    """Raised when isolation requirements cannot be met."""
    pass


class MutationBoundaryError(SimulationEnvironmentError):
    """Raised when mutation boundary is violated."""
    pass


class ForbiddenPathError(MutationBoundaryError):
    """Raised when attempting to mutate forbidden paths."""
    pass


class MaxFilesExceededError(MutationBoundaryError):
    """Raised when maximum files changed is exceeded."""
    pass


class MaxBytesExceededError(MutationBoundaryError):
    """Raised when maximum bytes written is exceeded."""
    pass


class UndeclaredFileError(MutationBoundaryError):
    """Raised when attempting to mutate undeclared files."""
    pass


class MutationError(SimulationEnvironmentError):
    """Raised when mutation fails."""
    pass


class ExecutionError(SimulationEnvironmentError):
    """Raised when execution fails."""
    pass


class VerificationError(SimulationEnvironmentError):
    """Raised when verification fails."""
    pass


class TargetProtectionError(SimulationEnvironmentError):
    """Raised when real target protection is violated."""
    pass


class TargetModifiedError(TargetProtectionError):
    """Raised when real target was modified."""
    pass
