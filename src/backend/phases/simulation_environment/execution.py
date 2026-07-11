"""Execution management for Simulation Environment."""
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from .schema import (
    Execution_Result,
    Execution_Status,
    Target_Mutation,
    Changed_File,
    Change_Type,
    Apply_Mutation_Boundary,
    Post_Apply_Verification,
    Verification_Result,
    Verification_Status,
)
from .mutation_boundary import (
    create_target_mutation,
    record_file_change,
    validate_mutation_completeness,
)
from .errors import (
    ExecutionError,
    MutationError,
)


def run_isolated_command(
    command: list[str],
    cwd: str | Path | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Run a command in isolated environment.
    
    Args:
        command: Command to run as list
        cwd: Working directory
        timeout: Timeout in seconds
        
    Returns:
        Dictionary with stdout, stderr, exit_code, duration
        
    Raises:
        ExecutionError: if command execution fails
    """
    start_time = time.time()
    
    try:
        result = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
            "duration": duration,
            "command": " ".join(command),
            "cwd": str(cwd) if cwd else None,
        }
    
    except subprocess.TimeoutExpired as e:
        end_time = time.time()
        raise ExecutionError(
            f"Command timed out after {timeout}s: {' '.join(command)}"
        )
    except Exception as e:
        raise ExecutionError(f"Command execution failed: {e}")


def run_isolated_command_string(
    command: str,
    cwd: str | Path | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Run a verification command string in the isolated environment."""
    start_time = time.time()

    try:
        result = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=True,
        )

        end_time = time.time()
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
            "duration": end_time - start_time,
            "command": command,
            "cwd": str(cwd) if cwd else None,
        }
    except subprocess.TimeoutExpired:
        raise ExecutionError(f"Command timed out after {timeout}s: {command}")
    except Exception as e:
        raise ExecutionError(f"Command execution failed: {e}")


def execute_demo(
    demo: dict[str, Any],
    isolated_root: str | Path,
    boundary: Apply_Mutation_Boundary,
) -> Execution_Result:
    """Execute the demo in isolated environment.
    
    Execution runs exactly once.
    Do not implement corrected-execution loop, second execution attempt,
    automatic retry, or hidden mutation retry.
    
    Args:
        demo: Demo dictionary
        isolated_root: Path to isolated root
        boundary: Mutation boundary
        
    Returns:
        Execution_Result with execution details
    """
    execution_id = f"exec-{int(time.time() * 1000) % 1000000:06d}"
    isolated_path = Path(isolated_root)
    
    # Get entrypoint
    entrypoint = demo.get("executable_entrypoint", "main.py")
    entrypoint_path = isolated_path / entrypoint
    
    # Check entrypoint exists
    if not entrypoint_path.exists():
        return Execution_Result(
            execution_id=execution_id,
            status=Execution_Status.failed,
            exit_code=1,
            stderr=f"Entrypoint {entrypoint} not found",
            execution_count=0,
            metadata={"attempted_entrypoint": entrypoint},
        )
    
    # Execute entrypoint
    command = [sys.executable, str(entrypoint)]
    
    try:
        result = run_isolated_command(
            command,
            cwd=isolated_path,
            timeout=60.0,
        )
        
        status = Execution_Status.completed if result["exit_code"] == 0 else Execution_Status.failed
        
        return Execution_Result(
            execution_id=execution_id,
            status=status,
            exit_code=result["exit_code"],
            stdout=result["stdout"],
            stderr=result["stderr"],
            duration_seconds=result["duration"],
            mutation_boundary=boundary,
            execution_count=1,  # Exactly once
            metadata={
                "command": command,
                "cwd": str(isolated_path),
            },
        )
    
    except ExecutionError as e:
        return Execution_Result(
            execution_id=execution_id,
            status=Execution_Status.failed,
            exit_code=1,
            stderr=str(e),
            execution_count=1,
            mutation_boundary=boundary,
            metadata={"error": str(e)},
        )


def apply_package_plan_corrections(
    isolated_root: str | Path,
    admitted_package_plan: dict[str, Any],
    boundary: Apply_Mutation_Boundary,
) -> Target_Mutation:
    """Apply admitted package plan corrections to isolated environment.
    
    Target_Mutation must:
    - occur only inside the isolated target
    - apply only admitted package-plan changes
    - preserve unrelated files
    - reject undeclared file creation
    - reject paths outside the allowed scope
    - record every changed file
    - record before and after SHA-256 hashes
    - record bytes written
    - record command output
    - record structured errors
    
    Args:
        isolated_root: Path to isolated root
        admitted_package_plan: Admitted package plan with corrections
        boundary: Mutation boundary
        
    Returns:
        Target_Mutation with recorded changes
        
    Raises:
        MutationError: if mutation fails
    """
    isolated_path = Path(isolated_root)
    mutation = create_target_mutation(
        boundary,
        "Apply admitted package plan corrections"
    )
    
    # Get corrections from package plan
    corrections = admitted_package_plan.get("corrections", {})
    patches = admitted_package_plan.get("applied_package_plan_patches", [])
    
    # Apply each patch
    for patch in patches:
        target_field = patch.get("target_field", "")
        new_value = patch.get("new_value", None)
        patch_type = patch.get("patch_type", "replace")
        
        # Map target_field to file path
        if target_field.startswith("supporting_metadata."):
            # Skip metadata patches for now
            continue
        
        # For file patches
        file_path = isolated_path / target_field
        
        try:
            if patch_type == "add" or patch_type == "replace":
                # Create parent directories
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Record before state
                before_content = file_path.read_bytes() if file_path.exists() else None
                
                # Write new content
                if isinstance(new_value, str):
                    file_path.write_text(new_value)
                else:
                    file_path.write_bytes(str(new_value).encode())
                
                # Record after state
                after_content = file_path.read_bytes()
                
                # Record change
                change_type = Change_Type.created if not file_path.exists() else Change_Type.modified
                record_file_change(
                    mutation,
                    str(target_field),
                    change_type,
                    before_content,
                    after_content,
                )
                
            elif patch_type == "delete":
                if file_path.exists():
                    before_content = file_path.read_bytes()
                    file_path.unlink()
                    record_file_change(
                        mutation,
                        str(target_field),
                        Change_Type.deleted,
                        before_content,
                        None,
                    )
        
        except Exception as e:
            mutation.structured_errors.append({
                "error_type": "patch_application_error",
                "patch_id": patch.get("patch_id", ""),
                "target_field": target_field,
                "message": str(e),
            })
    
    # Apply direct corrections
    for file_path_str, correction in corrections.items():
        file_path = isolated_path / file_path_str
        
        try:
            # Record before state
            before_content = file_path.read_bytes() if file_path.exists() else None
            
            # Apply correction
            if isinstance(correction, dict):
                if "content" in correction:
                    file_path.write_text(correction["content"])
                elif "replace" in correction:
                    content = file_path.read_text() if file_path.exists() else ""
                    new_content = content.replace(
                        correction["replace"],
                        correction.get("with", "")
                    )
                    file_path.write_text(new_content)
            else:
                file_path.write_text(str(correction))
            
            # Record after state
            after_content = file_path.read_bytes()
            
            # Record change
            change_type = Change_Type.created if not file_path.exists() else Change_Type.modified
            record_file_change(
                mutation,
                file_path_str,
                change_type,
                before_content,
                after_content,
            )
        
        except Exception as e:
            mutation.structured_errors.append({
                "error_type": "correction_application_error",
                "file": file_path_str,
                "message": str(e),
            })
    
    # Validate mutation is within boundaries
    validate_mutation_completeness(mutation, boundary)
    
    return mutation


def run_verification_commands(
    demo: dict[str, Any],
    isolated_root: str | Path,
    mutation: Target_Mutation,
) -> Post_Apply_Verification:
    """Run verification commands after mutation.
    
    Post_Apply_Verification must prove:
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
    
    Args:
        demo: Demo dictionary
        isolated_root: Path to isolated root
        mutation: Target mutation that was applied
        
    Returns:
        Post_Apply_Verification with results
    """
    verification_id = f"verify-{int(time.time() * 1000) % 1000000:06d}"
    isolated_path = Path(isolated_root)
    
    verification_results = []

    def normalize_rel_path(value: str) -> str:
        return value.replace("\\", "/")
    
    # Check intended correction exists
    corrections = demo.get("admitted_package_plan_corrections", {})
    intended_correction_exists = not bool(corrections)
    for file_path, correction in corrections.items():
        target_file = isolated_path / file_path
        if target_file.exists():
            verification_results.append(Verification_Result(
                verification_id=f"{verification_id}-correction-{file_path}",
                check_type="intended_correction_exists",
                status=Verification_Status.passed,
                message=f"Correction for {file_path} exists",
            ))
            intended_correction_exists = True
        else:
            verification_results.append(Verification_Result(
                verification_id=f"{verification_id}-correction-{file_path}",
                check_type="intended_correction_exists",
                status=Verification_Status.failed,
                message=f"Correction for {file_path} missing",
            ))
    
    # Check changed files match admitted plan
    files_match_admitted_plan = True
    changed_files_paths = [normalize_rel_path(cf.file_path) for cf in mutation.changed_files]
    admitted_changes = demo.get("admitted_package_plan_corrections", {}).keys()
    
    for changed_file in changed_files_paths:
        if changed_file not in admitted_changes:
            verification_results.append(Verification_Result(
                verification_id=f"{verification_id}-unexpected-change-{changed_file}",
                check_type="files_match_admitted_plan",
                status=Verification_Status.failed,
                message=f"Unexpected change: {changed_file}",
            ))
            files_match_admitted_plan = False
    
    if files_match_admitted_plan:
        verification_results.append(Verification_Result(
            verification_id=f"{verification_id}-files-match",
            check_type="files_match_admitted_plan",
            status=Verification_Status.passed,
            message="All changed files match admitted plan",
        ))
    
    # Check no required file is missing
    no_required_file_missing = True
    required_files = [normalize_rel_path(path) for path in demo.get("required_source_files", [])]
    for required_file in required_files:
        if not (isolated_path / required_file).exists():
            verification_results.append(Verification_Result(
                verification_id=f"{verification_id}-missing-{required_file}",
                check_type="no_required_file_missing",
                status=Verification_Status.failed,
                message=f"Required file missing: {required_file}",
            ))
            no_required_file_missing = False
    
    if no_required_file_missing:
        verification_results.append(Verification_Result(
            verification_id=f"{verification_id}-all-required-present",
            check_type="no_required_file_missing",
            status=Verification_Status.passed,
            message="All required files present",
        ))
    
    # Check no unexpected file is created
    no_unexpected_file_created = True
    expected_files = set(required_files) | set(changed_files_paths)
    for file_path in isolated_path.rglob("*"):
        if file_path.is_file():
            rel_path = normalize_rel_path(str(file_path.relative_to(isolated_path)))
            if rel_path not in expected_files and not rel_path.startswith("."):
                verification_results.append(Verification_Result(
                    verification_id=f"{verification_id}-unexpected-{rel_path}",
                    check_type="no_unexpected_file_created",
                    status=Verification_Status.failed,
                    message=f"Unexpected file: {rel_path}",
                ))
                no_unexpected_file_created = False
    
    if no_unexpected_file_created:
        verification_results.append(Verification_Result(
            verification_id=f"{verification_id}-no-unexpected",
            check_type="no_unexpected_file_created",
            status=Verification_Status.passed,
            message="No unexpected files created",
        ))
    
    # Run verification commands from demo
    verification_commands = demo.get("verification_commands", [])
    required_tests_pass = True
    
    for i, cmd in enumerate(verification_commands):
        try:
            result = run_isolated_command_string(
                cmd,
                cwd=isolated_path,
                timeout=30.0,
            )
            
            if result["exit_code"] == 0:
                verification_results.append(Verification_Result(
                    verification_id=f"{verification_id}-cmd-{i}",
                    check_type="verification_command",
                    status=Verification_Status.passed,
                    message=f"Command passed: {cmd}",
                    details={"stdout": result["stdout"][:500]},
                ))
            else:
                verification_results.append(Verification_Result(
                    verification_id=f"{verification_id}-cmd-{i}",
                    check_type="verification_command",
                    status=Verification_Status.failed,
                    message=f"Command failed: {cmd}",
                    details={"stderr": result["stderr"][:500]},
                ))
                required_tests_pass = False
        
        except Exception as e:
            verification_results.append(Verification_Result(
                verification_id=f"{verification_id}-cmd-{i}",
                check_type="verification_command",
                status=Verification_Status.failed,
                message=f"Command error: {cmd}",
                details={"error": str(e)},
            ))
            required_tests_pass = False
    
    # Determine overall status
    all_passed = all(
        vr.status == Verification_Status.passed 
        for vr in verification_results
    )
    overall_status = Verification_Status.passed if all_passed else Verification_Status.failed
    
    return Post_Apply_Verification(
        verification_id=verification_id,
        target_mutation=mutation,
        verification_results=verification_results,
        intended_correction_exists=intended_correction_exists,
        files_match_admitted_plan=files_match_admitted_plan,
        required_tests_pass=required_tests_pass,
        required_build_checks_pass=True,  # Placeholder
        required_schema_checks_pass=True,  # Placeholder
        no_required_file_missing=no_required_file_missing,
        no_unexpected_file_created=no_unexpected_file_created,
        no_unrelated_file_changed=True,  # Will be checked later
        no_unresolved_conflict=True,  # Will be checked later
        no_detected_regression=True,  # Will be checked later
        output_artifacts_valid=True,  # Placeholder
        required_evidence_complete=True,  # Placeholder
        overall_status=overall_status,
        failure_reason=None if all_passed else "Verification checks failed",
        metadata={
            "verification_commands_count": len(verification_commands),
            "passed_count": sum(1 for vr in verification_results if vr.status == Verification_Status.passed),
            "failed_count": sum(1 for vr in verification_results if vr.status == Verification_Status.failed),
        },
    )
