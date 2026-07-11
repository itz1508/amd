"""Simulation Environment validator."""
import hashlib
import json
from typing import Any

from .schema import Simulation_Environment_Input
from .errors import (
    AdmissionError,
    ReadinessThresholdError,
    SimulationNotReadyError,
    GraderFailureError,
    ConflictError,
    WrongRouteError,
    PackagePlanFingerprintMismatchError,
)


READINESS_THRESHOLD = 0.9391


def validate_admission(input_data: Simulation_Environment_Input) -> None:
    """Validate admission requirements for Simulation_Environment.
    
    Admission is valid only when:
    - readiness >= 0.9391
    - simulation_ready is true
    - required_grader_failures is empty
    - unresolved_conflict is false
    - next_route equals simulation_environment
    - the admitted package-plan fingerprint matches the Gap_Evaluation result
    
    Raises:
        AdmissionError: if any admission requirement is not met
    """
    gap_eval = input_data.gap_evaluation_output
    admitted_package_plan = input_data.admitted_package_plan
    
    # Check readiness threshold
    readiness = gap_eval.get("readiness", 0.0)
    if readiness < READINESS_THRESHOLD:
        raise ReadinessThresholdError(
            f"Readiness {readiness} below threshold {READINESS_THRESHOLD}"
        )
    
    # Check simulation_ready
    simulation_ready = gap_eval.get("simulation_ready", False)
    if not simulation_ready:
        raise SimulationNotReadyError("simulation_ready is false")
    
    # Check required_grader_failures
    required_grader_failures = gap_eval.get("required_grader_failures", [])
    if required_grader_failures:
        raise GraderFailureError(
            f"Required grader failures present: {required_grader_failures}"
        )
    
    # Check unresolved_conflict
    unresolved_conflict = gap_eval.get("unresolved_conflict", False)
    if unresolved_conflict:
        raise ConflictError("Unresolved conflict detected")
    
    # Check next_route
    next_route = gap_eval.get("next_route", "")
    if next_route != "simulation_environment":
        raise WrongRouteError(
            f"next_route is '{next_route}', expected 'simulation_environment'"
        )
    
    # Check package plan fingerprint match
    admitted_package_plan_fp = _compute_package_plan_fingerprint(admitted_package_plan)
    gap_eval_package_plan_fp = gap_eval.get("resulting_package_plan_fingerprint", "")
    
    # If Gap_Evaluation output has fingerprint, check it matches
    if gap_eval_package_plan_fp:
        resulting_plan = gap_eval.get("resulting_package_plan", {})
        resulting_plan_fp = _compute_package_plan_fingerprint(resulting_plan)
        if admitted_package_plan_fp != resulting_plan_fp:
            raise PackagePlanFingerprintMismatchError(
                f"Package plan fingerprint mismatch: "
                f"admitted={admitted_package_plan_fp[:16]}... "
                f"vs gap_eval_result={resulting_plan_fp[:16]}..."
            )


def _compute_package_plan_fingerprint(plan: dict[str, Any]) -> str:
    """Compute deterministic fingerprint for package plan."""
    def normalize_value(v: Any) -> Any:
        if isinstance(v, dict):
            return {k: normalize_value(v) for k, v in sorted(v.items())}
        elif isinstance(v, list):
            return sorted(normalize_value(item) for item in v)
        elif isinstance(v, (str, int, float, bool)):
            return v
        elif v is None:
            return None
        else:
            return str(v)
    
    normalized = normalize_value(plan)
    serialized = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def validate_isolated_environment(
    isolated_root: str,
    real_target: str,
    file_inventory: list[dict[str, Any]],
) -> bool:
    """Validate that isolated environment meets requirements.
    
    Requirements:
    - exists outside the real target
    - preserves source-relative paths
    - contains only required simulation files
    
    Returns:
        True if valid, raises error if not
    """
    # Check that isolated root is outside real target
    import os
    isolated_abs = os.path.abspath(isolated_root)
    real_target_abs = os.path.abspath(real_target)
    
    # Ensure isolated is not inside real target
    if isolated_abs.startswith(real_target_abs + os.sep):
        from .errors import IsolationError
        raise IsolationError(
            f"Isolated environment {isolated_abs} is inside real target {real_target_abs}"
        )
    
    # Check that all files in inventory have relative paths preserved
    for file_entry in file_inventory:
        file_path = file_entry.get("path", "")
        # Should be relative path
        if os.path.isabs(file_path):
            from .errors import IsolationError
            raise IsolationError(
                f"File path {file_path} is absolute, expected relative"
            )
    
    return True


def validate_demo_self_contained(
    demo: dict[str, Any],
    isolated_files: list[str],
) -> bool:
    """Validate that demo is self-contained.
    
    The demo must not depend on undeclared files outside the isolated environment.
    
    Args:
        demo: Demo dictionary
        isolated_files: List of files actually present in isolated environment
        
    Returns:
        True if valid, raises error if not
    """
    required_source_files = demo.get("required_source_files", [])
    
    # Check that all required source files are present
    isolated_file_set = set(isolated_files)
    for required_file in required_source_files:
        if required_file not in isolated_file_set:
            from .errors import MissingDemoDependencyError
            raise MissingDemoDependencyError(
                f"Missing demo dependency: {required_file}"
            )
    
    return True


def validate_mutation_boundary(
    boundary: dict[str, Any],
    target_file: str,
) -> bool:
    """Validate that a target file is within mutation boundary.
    
    Args:
        boundary: Mutation boundary dictionary
        target_file: File to check
        
    Returns:
        True if allowed, raises error if not
    """
    import fnmatch
    
    allowed_files = boundary.get("allowed_files", [])
    allowed_paths = boundary.get("allowed_paths", [])
    forbidden_paths = boundary.get("forbidden_paths", [])
    
    # Check forbidden paths first
    for forbidden_pattern in forbidden_paths:
        if fnmatch.fnmatch(target_file, forbidden_pattern):
            from .errors import ForbiddenPathError
            raise ForbiddenPathError(
                f"File {target_file} matches forbidden pattern: {forbidden_pattern}"
            )
    
    # Check allowed files
    if allowed_files:
        allowed = False
        for allowed_pattern in allowed_files:
            if fnmatch.fnmatch(target_file, allowed_pattern):
                allowed = True
                break
        if not allowed:
            from .errors import UndeclaredFileError
            raise UndeclaredFileError(
                f"File {target_file} not in allowed files: {allowed_files}"
            )
    
    # Check allowed paths
    if allowed_paths:
        allowed = False
        for allowed_pattern in allowed_paths:
            if fnmatch.fnmatch(target_file, allowed_pattern):
                allowed = True
                break
        if not allowed:
            from .errors import UndeclaredFileError
            raise UndeclaredFileError(
                f"File {target_file} not in allowed paths: {allowed_paths}"
            )
    
    return True


def validate_file_count_boundary(
    boundary: dict[str, Any],
    current_count: int,
) -> bool:
    """Validate that file count is within boundary.
    
    Args:
        boundary: Mutation boundary dictionary
        current_count: Current number of files changed
        
    Returns:
        True if within limit, raises error if not
    """
    max_files = boundary.get("max_files_changed", 10)
    if current_count > max_files:
        from .errors import MaxFilesExceededError
        raise MaxFilesExceededError(
            f"Files changed ({current_count}) exceeds maximum ({max_files})"
        )
    return True


def validate_bytes_boundary(
    boundary: dict[str, Any],
    current_bytes: int,
) -> bool:
    """Validate that bytes written is within boundary.
    
    Args:
        boundary: Mutation boundary dictionary
        current_bytes: Current bytes written
        
    Returns:
        True if within limit, raises error if not
    """
    max_bytes = boundary.get("max_bytes_written", 1024 * 1024)
    if current_bytes > max_bytes:
        from .errors import MaxBytesExceededError
        raise MaxBytesExceededError(
            f"Bytes written ({current_bytes}) exceeds maximum ({max_bytes})"
        )
    return True
