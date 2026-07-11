"""Simulation Environment schema definitions."""
from dataclasses import dataclass, field
from typing import Any
from enum import Enum
import hashlib
import json


class Execution_Status(str, Enum):
    """Execution status enumerations."""
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    timed_out = "timed_out"


class Verification_Status(str, Enum):
    """Verification status enumerations."""
    pending = "pending"
    passed = "passed"
    failed = "failed"
    skipped = "skipped"


class Change_Type(str, Enum):
    """Change type enumerations."""
    created = "created"
    modified = "modified"
    deleted = "deleted"
    unchanged = "unchanged"


@dataclass
class Changed_File:
    """Record of a changed file during mutation.
    
    Records:
    - file_path: Relative path from isolated root
    - change_type: created, modified, deleted, unchanged
    - before_hash: SHA-256 hash before change
    - after_hash: SHA-256 hash after change
    - bytes_written: Number of bytes written
    - command_output: Output from any commands that affected this file
    - structured_errors: Any structured errors related to this file
    """
    file_path: str
    change_type: Change_Type
    before_hash: str
    after_hash: str
    bytes_written: int = 0
    command_output: str = ""
    structured_errors: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": self.file_path,
            "change_type": self.change_type.value,
            "before_hash": self.before_hash,
            "after_hash": self.after_hash,
            "bytes_written": self.bytes_written,
            "command_output": self.command_output,
            "structured_errors": list(self.structured_errors),
            "metadata": dict(self.metadata),
        }


@dataclass
class Verification_Result:
    """Result of a single verification check.
    
    Contains:
    - verification_id: Unique identifier for this verification
    - check_type: Type of verification performed
    - status: passed, failed, skipped
    - message: Human-readable description
    - details: Additional structured details
    """
    verification_id: str
    check_type: str
    status: Verification_Status
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "verification_id": self.verification_id,
            "check_type": self.check_type,
            "status": self.status.value,
            "message": self.message,
            "details": dict(self.details),
            "metadata": dict(self.metadata),
        }


@dataclass
class Target_Mutation:
    """Record of mutation applied to target in isolated environment.
    
    Contains:
    - mutation_id: Unique identifier
    - description: What was mutated
    - changed_files: List of Changed_File records
    - command_output: Output from mutation commands
    - structured_errors: Any structured errors
    """
    mutation_id: str
    description: str
    changed_files: list[Changed_File] = field(default_factory=list)
    command_output: str = ""
    structured_errors: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mutation_id": self.mutation_id,
            "description": self.description,
            "changed_files": [cf.to_dict() for cf in self.changed_files],
            "command_output": self.command_output,
            "structured_errors": list(self.structured_errors),
            "metadata": dict(self.metadata),
        }


@dataclass
class Apply_Mutation_Boundary:
    """Definition of mutation boundary constraints.
    
    Contains:
    - allowed_files: List of file patterns allowed for mutation
    - allowed_paths: List of path patterns allowed for mutation
    - forbidden_paths: List of path patterns forbidden for mutation
    - allowed_commands: List of commands allowed during mutation
    - max_files_changed: Maximum number of files that can be changed
    - max_bytes_written: Maximum total bytes that can be written
    - admitted_package_plan_operations: List of operations allowed by package plan
    - rollback_evidence: Evidence for rollback capability
    """
    allowed_files: list[str] = field(default_factory=list)
    allowed_paths: list[str] = field(default_factory=list)
    forbidden_paths: list[str] = field(default_factory=list)
    allowed_commands: list[str] = field(default_factory=list)
    max_files_changed: int = 10
    max_bytes_written: int = 1024 * 1024  # 1MB default
    admitted_package_plan_operations: list[str] = field(default_factory=list)
    rollback_evidence: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed_files": list(self.allowed_files),
            "allowed_paths": list(self.allowed_paths),
            "forbidden_paths": list(self.forbidden_paths),
            "allowed_commands": list(self.allowed_commands),
            "max_files_changed": self.max_files_changed,
            "max_bytes_written": self.max_bytes_written,
            "admitted_package_plan_operations": list(self.admitted_package_plan_operations),
            "rollback_evidence": dict(self.rollback_evidence),
            "metadata": dict(self.metadata),
        }


@dataclass
class Post_Apply_Verification:
    """Post-apply verification results.
    
    Must prove:
    - the intended correction exists
    - changed files match the admitted package plan
    - required tests pass
    - required build checks pass
    - required schema checks pass
    - no required file is missing
    - no unexpected file is created
    - no unrelated file is changed
    - no unresolved conflict remains
    - no detected regression remains
    - output artifacts are valid
    - required evidence is complete
    """
    verification_id: str
    target_mutation: Target_Mutation | None = None
    verification_results: list[Verification_Result] = field(default_factory=list)
    intended_correction_exists: bool = False
    files_match_admitted_plan: bool = False
    required_tests_pass: bool = False
    required_build_checks_pass: bool = False
    required_schema_checks_pass: bool = False
    no_required_file_missing: bool = False
    no_unexpected_file_created: bool = False
    no_unrelated_file_changed: bool = False
    no_unresolved_conflict: bool = False
    no_detected_regression: bool = False
    output_artifacts_valid: bool = False
    required_evidence_complete: bool = False
    overall_status: Verification_Status = Verification_Status.pending
    failure_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result = {
            "verification_id": self.verification_id,
            "intended_correction_exists": self.intended_correction_exists,
            "files_match_admitted_plan": self.files_match_admitted_plan,
            "required_tests_pass": self.required_tests_pass,
            "required_build_checks_pass": self.required_build_checks_pass,
            "required_schema_checks_pass": self.required_schema_checks_pass,
            "no_required_file_missing": self.no_required_file_missing,
            "no_unexpected_file_created": self.no_unexpected_file_created,
            "no_unrelated_file_changed": self.no_unrelated_file_changed,
            "no_unresolved_conflict": self.no_unresolved_conflict,
            "no_detected_regression": self.no_detected_regression,
            "output_artifacts_valid": self.output_artifacts_valid,
            "required_evidence_complete": self.required_evidence_complete,
            "overall_status": self.overall_status.value,
            "failure_reason": self.failure_reason,
            "verification_results": [vr.to_dict() for vr in self.verification_results],
            "metadata": dict(self.metadata),
        }
        if self.target_mutation:
            result["target_mutation"] = self.target_mutation.to_dict()
        return result


@dataclass
class Execution_Result:
    """Result of execution in isolated environment.
    
    Execution runs exactly once.
    Do not implement corrected-execution loop, second execution attempt, 
    automatic retry, or hidden mutation retry.
    """
    execution_id: str
    status: Execution_Status
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    duration_seconds: float = 0.0
    mutation_boundary: Apply_Mutation_Boundary | None = None
    target_mutation: Target_Mutation | None = None
    post_apply_verification: Post_Apply_Verification | None = None
    changed_files: list[Changed_File] = field(default_factory=list)
    verification_results: list[Verification_Result] = field(default_factory=list)
    execution_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result = {
            "execution_id": self.execution_id,
            "status": self.status.value,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_seconds": self.duration_seconds,
            "execution_count": self.execution_count,
            "changed_files": [cf.to_dict() for cf in self.changed_files],
            "verification_results": [vr.to_dict() for vr in self.verification_results],
            "metadata": dict(self.metadata),
        }
        if self.mutation_boundary:
            result["mutation_boundary"] = self.mutation_boundary.to_dict()
        if self.target_mutation:
            result["target_mutation"] = self.target_mutation.to_dict()
        if self.post_apply_verification:
            result["post_apply_verification"] = self.post_apply_verification.to_dict()
        return result


@dataclass
class Self_Contained_Runtime_Demo:
    """Self-contained runtime demo for simulation.
    
    Contains:
    - required source files
    - admitted package-plan corrections
    - required configuration
    - dependency metadata
    - executable entrypoint
    - verification commands
    - expected success conditions
    - failure conditions
    - dossier evidence references
    
    The demo must not depend on undeclared files outside the isolated environment.
    """
    demo_id: str
    required_source_files: list[str] = field(default_factory=list)
    admitted_package_plan_corrections: dict[str, Any] = field(default_factory=dict)
    required_configuration: dict[str, Any] = field(default_factory=dict)
    dependency_metadata: dict[str, Any] = field(default_factory=dict)
    executable_entrypoint: str = ""
    verification_commands: list[str] = field(default_factory=list)
    expected_success_conditions: list[str] = field(default_factory=list)
    failure_conditions: list[str] = field(default_factory=list)
    dossier_evidence_refs: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "demo_id": self.demo_id,
            "required_source_files": list(self.required_source_files),
            "admitted_package_plan_corrections": dict(self.admitted_package_plan_corrections),
            "required_configuration": dict(self.required_configuration),
            "dependency_metadata": dict(self.dependency_metadata),
            "executable_entrypoint": self.executable_entrypoint,
            "verification_commands": list(self.verification_commands),
            "expected_success_conditions": list(self.expected_success_conditions),
            "failure_conditions": list(self.failure_conditions),
            "dossier_evidence_refs": list(self.dossier_evidence_refs),
            "metadata": dict(self.metadata),
        }

    def compute_fingerprint(self) -> str:
        """Compute deterministic fingerprint for the demo."""
        payload = {
            "demo_id": self.demo_id,
            "required_source_files": sorted(self.required_source_files),
            "admitted_package_plan_corrections": dict(sorted(self.admitted_package_plan_corrections.items())),
            "required_configuration": dict(sorted(self.required_configuration.items())),
            "dependency_metadata": dict(sorted(self.dependency_metadata.items())),
            "executable_entrypoint": self.executable_entrypoint,
            "verification_commands": sorted(self.verification_commands),
            "expected_success_conditions": sorted(self.expected_success_conditions),
            "failure_conditions": sorted(self.failure_conditions),
            "dossier_evidence_refs": sorted(self.dossier_evidence_refs),
        }
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


@dataclass
class Isolated_Runtime_Environment:
    """Isolated runtime environment for simulation.
    
    Requirements:
    - exists outside the real target
    - uses a separate writable location
    - preserves source-relative paths
    - contains only required simulation files
    - records source hashes
    - records isolated hashes
    - is reproducible from the same admitted input
    - never writes to the real target
    """
    environment_id: str
    isolated_root_path: str
    real_target_path: str
    file_inventory: list[dict[str, Any]] = field(default_factory=list)
    source_hashes: dict[str, str] = field(default_factory=dict)
    isolated_hashes: dict[str, str] = field(default_factory=dict)
    demo: Self_Contained_Runtime_Demo | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result = {
            "environment_id": self.environment_id,
            "isolated_root_path": self.isolated_root_path,
            "real_target_path": self.real_target_path,
            "file_inventory": list(self.file_inventory),
            "source_hashes": dict(self.source_hashes),
            "isolated_hashes": dict(self.isolated_hashes),
            "metadata": dict(self.metadata),
        }
        if self.demo:
            result["demo"] = self.demo.to_dict()
        return result

    def compute_fingerprint(self) -> str:
        """Compute deterministic fingerprint for the isolated environment."""
        demo_fp = self.demo.compute_fingerprint() if self.demo else ""
        payload = {
            "environment_id": self.environment_id,
            "isolated_root_path": self.isolated_root_path,
            "real_target_path": self.real_target_path,
            "file_inventory": sorted(self.file_inventory, key=lambda x: x.get("path", "")),
            "source_hashes": dict(sorted(self.source_hashes.items())),
            "isolated_hashes": dict(sorted(self.isolated_hashes.items())),
            "demo_fingerprint": demo_fp,
        }
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


@dataclass
class Simulation_Environment_Input:
    """Input boundary for Simulation_Environment phase.
    
    Consumes:
    - admitted Gap_Evaluation_Output
    - admitted package plan
    - supporting metadata
    - dossier evidence references
    - explicit isolated output location
    
    The implementation may use a typed fixture matching the frozen future Gap_Evaluation_Output.
    """
    gap_evaluation_output: dict[str, Any]
    admitted_package_plan: dict[str, Any]
    supporting_metadata: dict[str, Any] = field(default_factory=dict)
    dossier_evidence_refs: list[str] = field(default_factory=list)
    isolated_output_location: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "gap_evaluation_output": dict(self.gap_evaluation_output),
            "admitted_package_plan": dict(self.admitted_package_plan),
            "supporting_metadata": dict(self.supporting_metadata),
            "dossier_evidence_refs": list(self.dossier_evidence_refs),
            "isolated_output_location": self.isolated_output_location,
            "metadata": dict(self.metadata),
        }


@dataclass
class Simulation_Environment_Output:
    """Final Simulation_Environment artifact.
    
    Must contain:
    - phase
    - status
    - admitted_gap_evaluation_fingerprint
    - admitted_package_plan_fingerprint
    - isolated_environment_ref
    - isolated_environment_fingerprint
    - demo_fingerprint
    - execution_status
    - mutation_boundary
    - changed_files
    - verification_results
    - dossier_evidence_refs
    - failure_reason when applicable
    - next_route
    - simulation_environment_fingerprint
    """
    phase: str
    status: str
    admitted_gap_evaluation_fingerprint: str
    admitted_package_plan_fingerprint: str
    isolated_environment_ref: str
    isolated_environment_fingerprint: str
    demo_fingerprint: str
    execution_status: str
    mutation_boundary: dict[str, Any]
    changed_files: list[dict[str, Any]]
    verification_results: list[dict[str, Any]]
    dossier_evidence_refs: list[str]
    next_route: str
    failure_reason: str | None = None
    simulation_environment_fingerprint: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "status": self.status,
            "admitted_gap_evaluation_fingerprint": self.admitted_gap_evaluation_fingerprint,
            "admitted_package_plan_fingerprint": self.admitted_package_plan_fingerprint,
            "isolated_environment_ref": self.isolated_environment_ref,
            "isolated_environment_fingerprint": self.isolated_environment_fingerprint,
            "demo_fingerprint": self.demo_fingerprint,
            "execution_status": self.execution_status,
            "mutation_boundary": dict(self.mutation_boundary),
            "changed_files": list(self.changed_files),
            "verification_results": list(self.verification_results),
            "dossier_evidence_refs": list(self.dossier_evidence_refs),
            "failure_reason": self.failure_reason,
            "next_route": self.next_route,
            "simulation_environment_fingerprint": self.simulation_environment_fingerprint,
            "metadata": dict(self.metadata),
        }
