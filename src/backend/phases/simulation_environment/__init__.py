"""Simulation Environment phase package."""
from .runner import (
    run_simulation_environment,
    simulation_environment_fingerprint,
)
from .schema import (
    Simulation_Environment_Input,
    Simulation_Environment_Output,
    Isolated_Runtime_Environment,
    Self_Contained_Runtime_Demo,
    Apply_Mutation_Boundary,
    Target_Mutation,
    Post_Apply_Verification,
    Execution_Result,
    Changed_File,
    Verification_Result,
    Execution_Status,
    Verification_Status,
    Change_Type,
)
from .errors import (
    SimulationEnvironmentError,
    AdmissionError,
    ReadinessThresholdError,
    SimulationNotReadyError,
    GraderFailureError,
    ConflictError,
    WrongRouteError,
    PackagePlanFingerprintMismatchError,
    EnvironmentPreparationError,
    MissingDemoDependencyError,
    IsolationError,
    MutationBoundaryError,
    ForbiddenPathError,
    MaxFilesExceededError,
    MaxBytesExceededError,
    UndeclaredFileError,
    MutationError,
    ExecutionError,
    VerificationError,
    TargetProtectionError,
    TargetModifiedError,
)
from .validator import (
    validate_admission,
    validate_isolated_environment,
    validate_demo_self_contained,
    validate_mutation_boundary,
    validate_file_count_boundary,
    validate_bytes_boundary,
)
from .isolation import (
    create_isolated_environment,
    cleanup_isolated_environment,
    verify_isolation,
    compute_sha256,
    compute_directory_inventory,
)
from .demo import (
    build_demo,
    get_demo_entrypoint,
    get_demo_verification_commands,
    get_required_files,
)
from .mutation_boundary import (
    create_mutation_boundary,
    check_file_within_boundary,
    create_target_mutation,
    record_file_change,
    validate_mutation_completeness,
)
from .execution import (
    execute_demo,
    apply_package_plan_corrections,
    run_verification_commands,
    run_isolated_command,
)
from .verification import (
    complete_verification,
    check_unrelated_files_unchanged,
    check_no_unresolved_conflict,
    check_no_detected_regression,
)

__all__ = [
    # Runner
    "run_simulation_environment",
    "simulation_environment_fingerprint",
    
    # Schema
    "Simulation_Environment_Input",
    "Simulation_Environment_Output",
    "Isolated_Runtime_Environment",
    "Self_Contained_Runtime_Demo",
    "Apply_Mutation_Boundary",
    "Target_Mutation",
    "Post_Apply_Verification",
    "Execution_Result",
    "Changed_File",
    "Verification_Result",
    "Execution_Status",
    "Verification_Status",
    "Change_Type",
    
    # Errors
    "SimulationEnvironmentError",
    "AdmissionError",
    "ReadinessThresholdError",
    "SimulationNotReadyError",
    "GraderFailureError",
    "ConflictError",
    "WrongRouteError",
    "PackagePlanFingerprintMismatchError",
    "EnvironmentPreparationError",
    "MissingDemoDependencyError",
    "IsolationError",
    "MutationBoundaryError",
    "ForbiddenPathError",
    "MaxFilesExceededError",
    "MaxBytesExceededError",
    "UndeclaredFileError",
    "MutationError",
    "ExecutionError",
    "VerificationError",
    "TargetProtectionError",
    "TargetModifiedError",
    
    # Validator
    "validate_admission",
    "validate_isolated_environment",
    "validate_demo_self_contained",
    "validate_mutation_boundary",
    "validate_file_count_boundary",
    "validate_bytes_boundary",
    
    # Isolation
    "create_isolated_environment",
    "cleanup_isolated_environment",
    "verify_isolation",
    "compute_sha256",
    "compute_directory_inventory",
    
    # Demo
    "build_demo",
    "get_demo_entrypoint",
    "get_demo_verification_commands",
    "get_required_files",
    
    # Mutation Boundary
    "create_mutation_boundary",
    "check_file_within_boundary",
    "create_target_mutation",
    "record_file_change",
    "validate_mutation_completeness",
    
    # Execution
    "execute_demo",
    "apply_package_plan_corrections",
    "run_verification_commands",
    "run_isolated_command",
    
    # Verification
    "complete_verification",
    "check_unrelated_files_unchanged",
    "check_no_unresolved_conflict",
    "check_no_detected_regression",
]
