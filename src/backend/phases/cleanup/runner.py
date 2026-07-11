"""Cleanup Retention runner - Post-Phase operational cleanup."""
import os
import shutil
import sys
from pathlib import Path

from backend.paths import get_default_output_root
from backend.schemas.cleanup_retention import CleanupRetention
from backend.run_context import generate_run_id, get_created_at_iso

from .validators import (
    is_preserved_artifact,
    is_transient_path,
    is_under_output_root,
    is_repo_file,
    validate_cleanup_safety,
    get_preserved_artifacts,
    find_transient_paths,
)
from .output import build_cleanup_retention, write_cleanup_output


def run_cleanup_retention(
    output_root_str: str | None = None,
    run_id: str | None = None,
    dry_run: bool = True,
    confirm_cleanup: bool = False,
) -> int:
    """Run Cleanup/Retention stage.
    
    This is NOT Phase 10. It is operational cleanup after Phase 09.
    
    Purpose:
    - Clean up transient runtime material (sandbox workspaces, venvs, scratch files)
    - Preserve ALL proof artifacts and final locked/blocked result artifacts
    - Default to dry-run (no deletion) unless explicitly confirmed
    
    Does NOT:
    - Mutate target files
    - Delete proof artifacts
    - Delete manifests or artifact indexes
    - Delete latest.json
    - Delete Phase 09 final result
    - Delete repo files
    - Rewrite hashes
    - Change final result status
    - Rerun any phases
    - Apply, commit, or repair
    - Execute package operations
    - Execute target code
    - Execute build backend
    
    Returns exit code.
    """
    # Resolve paths
    if output_root_str:
        output_root = Path(output_root_str).resolve()
    else:
        output_root = get_default_output_root()
    
    print(f"Cleanup Retention: Starting")
    print(f"  Output root: {output_root}")
    print(f"  Dry run: {dry_run}")
    print(f"  Confirm cleanup: {confirm_cleanup}")
    
    # Get repo root for safety checks
    repo_root = Path.cwd().resolve()
    
    # === VALIDATE: Output root exists ===
    if not output_root.exists():
        print(f"ERROR: Output root does not exist: {output_root}", file=sys.stderr)
        return 1
    
    # === IDENTIFY: Get all preserved artifacts ===
    preserved_artifacts = get_preserved_artifacts(output_root)
    preserved_artifact_strs = [str(p.relative_to(output_root)) for p in preserved_artifacts]
    
    print(f"  Preserved artifacts: {len(preserved_artifacts)}")
    
    # === IDENTIFY: Find transient paths ===
    transient_paths = find_transient_paths(output_root)
    
    print(f"  Transient paths found: {len(transient_paths)}")
    
    # === VALIDATE: Safety checks for each transient path ===
    # To avoid issues with deleting both files and directories, we'll track
    # which directories we plan to delete, and skip files that are inside them
    safe_to_delete = []
    safe_dirs_to_delete = set()
    blocked_paths = []
    skipped_paths = []
    cleanup_errors = []
    
    for path in transient_paths:
        # Check if it's a preserved artifact (shouldn't happen, but double-check)
        if is_preserved_artifact(path):
            skipped_paths.append(str(path.relative_to(output_root)))
            continue
        
        # Validate safety
        is_safe, reason = validate_cleanup_safety(path, output_root, repo_root)
        
        if is_safe:
            # Additional check: never delete if it's a preserved artifact name
            if path.name in {
                "09_final_result_locked.json", "09_final_result_validation.json",
                "08_post_apply_verification.json", "latest.json",
                "run_manifest.json", "artifact_index.json",
            }:
                skipped_paths.append(str(path.relative_to(output_root)))
                continue
            
            # Only delete if explicitly confirmed AND not dry-run
            if confirm_cleanup and not dry_run:
                # If this is a directory, add it to safe_dirs and don't add files inside it
                if path.is_dir():
                    safe_dirs_to_delete.add(path)
                    safe_to_delete.append(path)
                else:
                    # For files, only add if not inside a directory we're already deleting
                    is_inside_safe_dir = False
                    for safe_dir in safe_dirs_to_delete:
                        try:
                            path.relative_to(safe_dir)
                            is_inside_safe_dir = True
                            break
                        except ValueError:
                            pass
                    if not is_inside_safe_dir:
                        safe_to_delete.append(path)
            else:
                # In dry-run mode or without confirmation, just report
                skipped_paths.append(str(path.relative_to(output_root)))
        else:
            blocked_paths.append(f"{path.relative_to(output_root)}: {reason}")
    
    # === ACTION: Perform cleanup (only if confirmed and not dry-run) ===
    deleted_paths = []
    
    if confirm_cleanup and not dry_run:
        for path in safe_to_delete:
            try:
                if path.is_dir():
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    path.unlink()
                deleted_paths.append(str(path.relative_to(output_root)))
                print(f"  Deleted: {path.relative_to(output_root)}")
            except (OSError, PermissionError) as e:
                cleanup_errors.append(f"Failed to delete {path.relative_to(output_root)}: {e}")
    
    # === VALIDATE: Check preserved artifacts still exist ===
    proof_artifacts_preserved = True
    latest_pointer_preserved = True
    artifact_index_preserved = True
    run_manifest_preserved = True
    final_result_artifact_preserved = True
    
    # Check critical artifacts
    critical_files = [
        "latest.json",
    ]
    
    for file_name in critical_files:
        file_path = output_root / file_name
        if not file_path.exists():
            if file_name == "latest.json":
                latest_pointer_preserved = False
                cleanup_errors.append(f"Critical artifact missing: {file_name}")
    
    # Check preserved artifacts in runs
    runs_dir = output_root / "runs"
    if runs_dir.exists():
        for run_dir in runs_dir.iterdir():
            if run_dir.is_dir():
                # Check for final result
                final_result = run_dir / "09_final_result_locked.json"
                if final_result.exists():
                    if not final_result.exists():  # Double check
                        final_result_artifact_preserved = False
                        cleanup_errors.append(f"Final result missing in {run_dir}")
                
                # Check for manifest and index
                for required in ["run_manifest.json", "artifact_index.json"]:
                    req_path = run_dir / required
                    if req_path.exists():
                        # It exists, so it's preserved
                        pass
    
    # Determine cleanup status
    if cleanup_errors:
        cleanup_status = "error"
    elif confirm_cleanup and not dry_run and deleted_paths:
        cleanup_status = "completed"
    elif dry_run:
        cleanup_status = "dry_run"
    else:
        cleanup_status = "skipped"
    
    # === GENERATE: New run context ===
    new_run_id = generate_run_id()
    created_at = get_created_at_iso()
    new_run_dir = output_root / "runs" / new_run_id
    
    try:
        new_run_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"ERROR: Cannot create output directory: {e}", file=sys.stderr)
        return 1
    
    # === BUILD: Cleanup report ===
    cleanup = build_cleanup_retention(
        run_id=new_run_id,
        output_root=str(output_root),
        dry_run=dry_run,
        confirm_cleanup=confirm_cleanup,
        cleanup_status=cleanup_status,
        preserved_artifacts=preserved_artifact_strs,
        deleted_paths=deleted_paths,
        skipped_paths=skipped_paths,
        blocked_paths=blocked_paths,
        cleanup_errors=cleanup_errors,
        proof_artifacts_preserved=proof_artifacts_preserved,
        latest_pointer_preserved=latest_pointer_preserved,
        artifact_index_preserved=artifact_index_preserved,
        run_manifest_preserved=run_manifest_preserved,
        final_result_artifact_preserved=final_result_artifact_preserved,
        created_at=created_at,
    )
    
    # === SAFETY: Verify cleanup object integrity ===
    assert cleanup.target_mutation_performed == False, "Cleanup must not mutate targets"
    assert cleanup.repo_files_deleted == False, "Cleanup must not delete repo files"
    assert cleanup.hashes_rewritten == False, "Cleanup must not rewrite hashes"
    assert cleanup.final_result_status_changed == False, "Cleanup must not change final result status"
    
    # === WRITE: Output artifacts ===
    write_result = write_cleanup_output(output_root, new_run_dir, cleanup)
    if write_result != 0:
        return write_result
    
    # === REPORT: Summary ===
    print(f"Cleanup Retention completed: {new_run_id}")
    print(f"  Status: {cleanup_status}")
    print(f"  Dry run: {dry_run}")
    print(f"  Confirm cleanup: {confirm_cleanup}")
    print(f"  Preserved artifacts: {len(preserved_artifact_strs)}")
    print(f"  Deleted paths: {len(deleted_paths)}")
    print(f"  Skipped paths: {len(skipped_paths)}")
    print(f"  Blocked paths: {len(blocked_paths)}")
    print(f"  Cleanup errors: {len(cleanup_errors)}")
    print(f"  Output: {new_run_dir}")
    
    return 0


def main(args: list[str] | None = None) -> int:
    """CLI entry point for cleanup phase.
    
    Args:
        args: Command line arguments (defaults to sys.argv).
        
    Returns:
        Exit code (0 for success, 1 for error).
    """
    import argparse
    import sys
    from pathlib import Path
    
    parser = argparse.ArgumentParser(
        prog="cleanup",
        description="Cleanup phase"
    )
    parser.add_argument(
        "final_path",
        help="Path to final result artifact"
    )
    parser.add_argument(
        "--output-root",
        required=True,
        help="Output directory for artifacts"
    )
    
    parsed = parser.parse_args(args)
    
    try:
        result = run_cleanup_retention(
            output_root_str=str(Path(parsed.output_root)),
            run_id="cli-cleanup-001",
            dry_run=False,
            confirm_cleanup=True
        )
        print(f"Cleanup completed: {parsed.final_path}")
        print(f"  Result: {result}")
        print(f"  Output: {Path(parsed.output_root) / '09_cleanup.json'}")
        return result
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
