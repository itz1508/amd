"""Simulation Environment runner."""
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any

from .schema import (
    Simulation_Environment_Input,
    Simulation_Environment_Output,
    Isolated_Runtime_Environment,
    Self_Contained_Runtime_Demo,
    Apply_Mutation_Boundary,
    Target_Mutation,
    Execution_Result,
    Post_Apply_Verification,
    Execution_Status,
    Verification_Status,
)
from .validator import (
    validate_admission,
    _compute_package_plan_fingerprint,
)
from .isolation import (
    create_isolated_environment,
    cleanup_isolated_environment,
    verify_isolation,
    compute_sha256,
)
from .demo import build_demo
from .mutation_boundary import create_mutation_boundary
from .execution import (
    execute_demo,
    apply_package_plan_corrections,
    run_verification_commands,
)
from .verification import complete_verification
from .errors import (
    SimulationEnvironmentError,
    EnvironmentPreparationError,
    ExecutionError,
)


def simulation_environment_fingerprint(
    admitted_package_plan: dict[str, Any],
    isolated_env: Isolated_Runtime_Environment,
    mutation_boundary: Apply_Mutation_Boundary,
    changed_files: list[dict[str, Any]],
    verification_results: list[dict[str, Any]],
    final_route: str,
) -> str:
    """Compute deterministic fingerprint for simulation environment.
    
    Must include stable canonical content from:
    - admitted package plan
    - isolated file inventory
    - mutation boundary
    - changed-file records
    - before and after hashes
    - verification results
    - final route
    
    Exclude:
    - timestamps
    - run identifiers
    - temporary absolute paths
    - machine-specific paths
    - output-root location
    - artifact location
    
    Sort all collections before canonical serialization.
    """
    # Normalize package plan
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
    
    normalized_package_plan = normalize_value(admitted_package_plan)
    
    # Normalize isolated file inventory
    file_inventory = isolated_env.file_inventory if isolated_env else []
    normalized_inventory = sorted(file_inventory, key=lambda x: x.get("path", ""))
    
    # Normalize mutation boundary
    boundary_dict = mutation_boundary.to_dict() if mutation_boundary else {}
    normalized_boundary = normalize_value(boundary_dict)
    
    # Normalize changed files
    normalized_changed_files = sorted(changed_files, key=lambda x: x.get("file_path", ""))
    
    # Normalize verification results
    normalized_verification_results = sorted(
        verification_results, 
        key=lambda x: x.get("verification_id", "")
    )
    
    payload = {
        "admitted_package_plan": normalized_package_plan,
        "isolated_file_inventory": normalized_inventory,
        "mutation_boundary": normalized_boundary,
        "changed_files": normalized_changed_files,
        "verification_results": normalized_verification_results,
        "final_route": final_route,
    }
    
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _protect_real_target(
    real_target_path: str | Path,
    gap_evaluation_output: dict[str, Any],
) -> dict[str, Any]:
    """Record real target state for protection verification.
    
    Args:
        real_target_path: Path to real target
        gap_evaluation_output: Gap evaluation output
        
    Returns:
        Dictionary with target protection information
    """
    import os
    from pathlib import Path
    
    real_target = Path(real_target_path)
    protection_info = {
        "real_target_path": str(real_target.resolve()),
        "file_hashes": {},
        "file_sizes": {},
        "file_mtimes": {},
    }
    
    # Record file information for protection
    required_files = gap_evaluation_output.get("required_source_files", [])
    for file_path in required_files:
        full_path = real_target / file_path
        if full_path.exists():
            protection_info["file_hashes"][file_path] = compute_sha256(full_path)
            protection_info["file_sizes"][file_path] = full_path.stat().st_size
            try:
                protection_info["file_mtimes"][file_path] = full_path.stat().st_mtime
            except (OSError, AttributeError):
                protection_info["file_mtimes"][file_path] = None
    
    return protection_info


def _verify_real_target_unchanged(
    protection_info: dict[str, Any],
) -> bool:
    """Verify that real target files are unchanged.
    
    Args:
        protection_info: Target protection information
        
    Returns:
        True if real target is unchanged
        
    Raises:
        TargetModifiedError: if real target was modified
    """
    from pathlib import Path
    from .errors import TargetModifiedError
    
    real_target = Path(protection_info.get("real_target_path", "."))
    
    # Check each file
    for file_path, expected_hash in protection_info.get("file_hashes", {}).items():
        full_path = real_target / file_path
        if full_path.exists():
            current_hash = compute_sha256(full_path)
            if current_hash != expected_hash:
                raise TargetModifiedError(
                    f"Real target file {file_path} was modified"
                )
            
            # Check size
            expected_size = protection_info.get("file_sizes", {}).get(file_path, 0)
            current_size = full_path.stat().st_size
            if current_size != expected_size:
                raise TargetModifiedError(
                    f"Real target file {file_path} size changed: {expected_size} -> {current_size}"
                )
            
            # Check modification time (where reliable)
            expected_mtime = protection_info.get("file_mtimes", {}).get(file_path)
            if expected_mtime is not None:
                try:
                    current_mtime = full_path.stat().st_mtime
                    if current_mtime != expected_mtime:
                        # Modification times can differ slightly, so we allow some tolerance
                        import time
                        if abs(current_mtime - expected_mtime) > 1.0:  # 1 second tolerance
                            raise TargetModifiedError(
                                f"Real target file {file_path} mtime changed"
                            )
                except (OSError, AttributeError):
                    pass  # Skip mtime check if not available
    
    return True


def run_simulation_environment(
    input_data: Simulation_Environment_Input,
    output_root: Path | None = None,
) -> Simulation_Environment_Output:
    """Run Simulation_Environment phase.
    
    Canonical internal flow:
    Simulation_Environment
    → Isolated_Runtime_Environment
    → Self_Contained_Runtime_Demo
    → Execution
       → Apply_Mutation_Boundary
       → Target_Mutation
       → Post_Apply_Verification
    
    Execution is internal to Simulation_Environment.
    Do not expose Execution as a top-level phase.
    
    Args:
        input_data: Simulation_Environment_Input containing admitted Gap_Evaluation output
        output_root: Optional output directory for artifacts
        
    Returns:
        Simulation_Environment_Output artifact
        
    Raises:
        SimulationEnvironmentError: on validation or execution errors
    """
    # Step 1: Validate admission
    try:
        validate_admission(input_data)
    except Exception as e:
        # Admission failed - return failure route to final_result
        from .errors import AdmissionError
        return Simulation_Environment_Output(
            phase="simulation_environment",
            status="failed",
            admitted_gap_evaluation_fingerprint=input_data.gap_evaluation_output.get("gap_evaluation_fingerprint", ""),
            admitted_package_plan_fingerprint=_compute_package_plan_fingerprint(input_data.admitted_package_plan),
            isolated_environment_ref="",
            isolated_environment_fingerprint="",
            demo_fingerprint="",
            execution_status=Execution_Status.failed.value,
            mutation_boundary={},
            changed_files=[],
            verification_results=[],
            dossier_evidence_refs=list(input_data.dossier_evidence_refs),
            failure_reason=str(e),
            next_route="final_result",
            metadata={
                "admission_failed": True,
                "error_type": type(e).__name__,
            },
        )
    
    # Step 2: Build self-contained runtime demo
    try:
        # Determine real target path from gap evaluation or metadata
        real_target_path = input_data.supporting_metadata.get(
            "real_target_path", 
            input_data.isolated_output_location or "."
        )
        
        demo = build_demo(
            input_data.admitted_package_plan,
            input_data.supporting_metadata,
            input_data.dossier_evidence_refs,
            real_target_path,
        )
    except EnvironmentPreparationError as e:
        # Environment preparation failed - route to final_result
        return Simulation_Environment_Output(
            phase="simulation_environment",
            status="failed",
            admitted_gap_evaluation_fingerprint=input_data.gap_evaluation_output.get("gap_evaluation_fingerprint", ""),
            admitted_package_plan_fingerprint=_compute_package_plan_fingerprint(input_data.admitted_package_plan),
            isolated_environment_ref="",
            isolated_environment_fingerprint="",
            demo_fingerprint="",
            execution_status=Execution_Status.failed.value,
            mutation_boundary={},
            changed_files=[],
            verification_results=[],
            dossier_evidence_refs=list(input_data.dossier_evidence_refs),
            failure_reason=f"Environment preparation failed: {e}",
            next_route="final_result",
            metadata={
                "terminal_state": "failed_simulation_environment",
                "error": str(e),
            },
        )
    
    # Step 3: Create isolated runtime environment
    try:
        isolated_env = create_isolated_environment(
            real_target_path,
            demo,
            input_data.isolated_output_location or None,
        )
    except EnvironmentPreparationError as e:
        # Environment preparation failed - route to final_result
        return Simulation_Environment_Output(
            phase="simulation_environment",
            status="failed",
            admitted_gap_evaluation_fingerprint=input_data.gap_evaluation_output.get("gap_evaluation_fingerprint", ""),
            admitted_package_plan_fingerprint=_compute_package_plan_fingerprint(input_data.admitted_package_plan),
            isolated_environment_ref="",
            isolated_environment_fingerprint="",
            demo_fingerprint=demo.compute_fingerprint(),
            execution_status=Execution_Status.failed.value,
            mutation_boundary={},
            changed_files=[],
            verification_results=[],
            dossier_evidence_refs=list(input_data.dossier_evidence_refs),
            failure_reason=f"Isolated environment creation failed: {e}",
            next_route="final_result",
            metadata={
                "terminal_state": "failed_simulation_environment",
                "error": str(e),
            },
        )
    
    # Step 4: Create mutation boundary
    mutation_boundary = create_mutation_boundary(
        input_data.admitted_package_plan,
        input_data.supporting_metadata,
    )
    
    # Step 5: Protect real target
    protection_info = _protect_real_target(
        real_target_path,
        input_data.gap_evaluation_output,
    )
    
    try:
        # Step 6: Apply package plan corrections
        target_mutation = apply_package_plan_corrections(
            isolated_env.isolated_root_path,
            input_data.admitted_package_plan,
            mutation_boundary,
        )
        
        # Step 7: Execute demo (runs exactly once)
        execution_result = execute_demo(
            demo.to_dict(),
            isolated_env.isolated_root_path,
            mutation_boundary,
        )
        
        # Update execution with mutation
        execution_result.mutation_boundary = mutation_boundary
        execution_result.target_mutation = target_mutation
        
        # Step 8: Run verification commands
        post_verify = run_verification_commands(
            demo.to_dict(),
            isolated_env.isolated_root_path,
            target_mutation,
        )
        
        # Complete verification
        post_verify = complete_verification(
            post_verify,
            isolated_env.to_dict(),
            demo.to_dict(),
        )
        
        execution_result.post_apply_verification = post_verify
        
        # Step 9: Verify real target unchanged
        _verify_real_target_unchanged(protection_info)
        
        # Step 10: Determine success
        execution_success = execution_result.status == Execution_Status.completed
        verification_success = post_verify.overall_status == Verification_Status.passed
        
        if execution_success and verification_success:
            # Success route: simulation_environment → inspection
            final_status = "completed"
            next_route = "inspection"
            execution_status = Execution_Status.completed.value
        else:
            # Failure route: simulation_environment → gap_handoff → backend.llm → final_result
            final_status = "failed"
            next_route = "gap_handoff"
            execution_status = execution_result.status.value
        
        # Build output
        output = Simulation_Environment_Output(
            phase="simulation_environment",
            status=final_status,
            admitted_gap_evaluation_fingerprint=input_data.gap_evaluation_output.get("gap_evaluation_fingerprint", ""),
            admitted_package_plan_fingerprint=_compute_package_plan_fingerprint(input_data.admitted_package_plan),
            isolated_environment_ref=isolated_env.environment_id,
            isolated_environment_fingerprint=isolated_env.compute_fingerprint(),
            demo_fingerprint=demo.compute_fingerprint(),
            execution_status=execution_status,
            mutation_boundary=mutation_boundary.to_dict(),
            changed_files=[cf.to_dict() for cf in target_mutation.changed_files],
            verification_results=[vr.to_dict() for vr in post_verify.verification_results],
            dossier_evidence_refs=list(input_data.dossier_evidence_refs),
            failure_reason=None if execution_success and verification_success else post_verify.failure_reason,
            next_route=next_route,
            metadata={
                "execution_id": execution_result.execution_id,
                "verification_id": post_verify.verification_id,
                "changed_files_count": len(target_mutation.changed_files),
                "verification_results_count": len(post_verify.verification_results),
                "real_target_protected": True,
            },
        )
        
        # Compute fingerprint
        output.simulation_environment_fingerprint = simulation_environment_fingerprint(
            input_data.admitted_package_plan,
            isolated_env,
            mutation_boundary,
            [cf.to_dict() for cf in target_mutation.changed_files],
            [vr.to_dict() for vr in post_verify.verification_results],
            next_route,
        )
        
        # Step 11: Write artifact if output_root provided
        if output_root is not None:
            try:
                output_root.mkdir(parents=True, exist_ok=True)
                artifact_path = output_root / "06_simulation_environment.json"
                
                # Atomic write
                temp_path = artifact_path.with_suffix(".tmp")
                temp_path.write_text(
                    json.dumps(output.to_dict(), sort_keys=True, indent=2) + "\n",
                    encoding="utf-8",
                )
                temp_path.replace(artifact_path)  # Atomic replacement
                
            except OSError:
                pass
        
        # Step 12: Cleanup isolated environment
        cleanup_isolated_environment(isolated_env)
        
        return output
    
    except Exception as e:
        # Any error during execution or verification
        # Route to gap_handoff
        cleanup_isolated_environment(isolated_env)
        
        return Simulation_Environment_Output(
            phase="simulation_environment",
            status="failed",
            admitted_gap_evaluation_fingerprint=input_data.gap_evaluation_output.get("gap_evaluation_fingerprint", ""),
            admitted_package_plan_fingerprint=_compute_package_plan_fingerprint(input_data.admitted_package_plan),
            isolated_environment_ref=isolated_env.environment_id if isolated_env else "",
            isolated_environment_fingerprint=isolated_env.compute_fingerprint() if isolated_env else "",
            demo_fingerprint=demo.compute_fingerprint() if demo else "",
            execution_status=Execution_Status.failed.value,
            mutation_boundary=mutation_boundary.to_dict() if mutation_boundary else {},
            changed_files=[],
            verification_results=[],
            dossier_evidence_refs=list(input_data.dossier_evidence_refs),
            failure_reason=f"Simulation environment execution failed: {e}",
            next_route="gap_handoff",
            metadata={
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )


def main(args: list[str] | None = None) -> int:
    """CLI entry point for simulation_environment phase.
    
    Args:
        args: Command line arguments (defaults to sys.argv).
        
    Returns:
        Exit code (0 for success, 1 for error).
    """
    import argparse
    import json
    from pathlib import Path
    
    parser = argparse.ArgumentParser(
        prog="simulation_environment",
        description="Simulation environment phase"
    )
    parser.add_argument(
        "gap_path",
        help="Path to gap evaluation artifact"
    )
    parser.add_argument(
        "--output-root",
        required=True,
        help="Output directory for artifacts"
    )
    
    parsed = parser.parse_args(args)
    
    try:
        # Load gap evaluation data
        with open(parsed.gap_path, 'r', encoding='utf-8') as f:
            gap_data = json.load(f)
        
        input_data = Simulation_Environment_Input(
            gap_evaluation_output=gap_data,
            admitted_package_plan={},
            supporting_metadata={},
            dossier_evidence_refs=gap_data.get("dossier_evidence_refs", []),
            isolated_output_location=str(Path(parsed.output_root) / "06_simulation_environment"),
            metadata={}
        )
        
        result = run_simulation_environment(input_data, Path(parsed.output_root))
        print(f"Simulation environment completed: {parsed.gap_path}")
        print(f"  Status: {result.status}")
        print(f"  Output: {Path(parsed.output_root) / '06_simulation_environment.json'}")
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
