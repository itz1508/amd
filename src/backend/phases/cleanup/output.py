"""Cleanup Retention output handling."""
import json
from pathlib import Path
from typing import Any

from backend.schemas.cleanup_retention import CleanupRetention
from backend.schemas.artifact import RunManifest, LatestPointer, ArtifactIndex
from backend.artifact_store.writer import write_json_artifact
from backend.artifact_store.artifact_index import create_artifact_index, compute_artifact_hashes
from backend.run_context import get_created_at_iso


def build_cleanup_retention(
    run_id: str,
    output_root: str,
    dry_run: bool,
    confirm_cleanup: bool,
    cleanup_status: str,
    preserved_artifacts: list[str],
    deleted_paths: list[str],
    skipped_paths: list[str],
    blocked_paths: list[str],
    cleanup_errors: list[str],
    proof_artifacts_preserved: bool,
    latest_pointer_preserved: bool,
    artifact_index_preserved: bool,
    run_manifest_preserved: bool,
    final_result_artifact_preserved: bool,
    created_at: str,
) -> CleanupRetention:
    """Build CleanupRetention object."""
    return CleanupRetention(
        cleanup_status=cleanup_status,
        run_id=run_id,
        output_root=output_root,
        dry_run=dry_run,
        confirm_cleanup=confirm_cleanup,
        preserved_artifacts=preserved_artifacts,
        deleted_paths=deleted_paths,
        skipped_paths=skipped_paths,
        blocked_paths=blocked_paths,
        cleanup_errors=cleanup_errors,
        proof_artifacts_preserved=proof_artifacts_preserved,
        latest_pointer_preserved=latest_pointer_preserved,
        artifact_index_preserved=artifact_index_preserved,
        run_manifest_preserved=run_manifest_preserved,
        final_result_artifact_preserved=final_result_artifact_preserved,
        # Fixed safety values - must never be True
        target_mutation_performed=False,
        repo_files_deleted=False,
        hashes_rewritten=False,
        final_result_status_changed=False,
        created_at=created_at,
    )


def write_cleanup_output(
    output_root: Path,
    run_dir: Path,
    cleanup: CleanupRetention,
) -> int:
    """Write all cleanup output artifacts. Returns exit code."""
    try:
        # Write main cleanup report
        write_json_artifact(
            run_dir / "cleanup_report.json",
            cleanup.to_dict(),
        )
        
        # Write validation artifact
        validation_data = {
            "run_id": cleanup.run_id,
            "phase": "cleanup",
            "cleanup_status": cleanup.cleanup_status,
            "dry_run": cleanup.dry_run,
            "confirm_cleanup": cleanup.confirm_cleanup,
            "preserved_artifacts_count": len(cleanup.preserved_artifacts),
            "deleted_paths_count": len(cleanup.deleted_paths),
            "skipped_paths_count": len(cleanup.skipped_paths),
            "blocked_paths_count": len(cleanup.blocked_paths),
            "cleanup_errors_count": len(cleanup.cleanup_errors),
            "proof_artifacts_preserved": cleanup.proof_artifacts_preserved,
            "latest_pointer_preserved": cleanup.latest_pointer_preserved,
            "artifact_index_preserved": cleanup.artifact_index_preserved,
            "run_manifest_preserved": cleanup.run_manifest_preserved,
            "final_result_artifact_preserved": cleanup.final_result_artifact_preserved,
            "target_mutation_performed": cleanup.target_mutation_performed,
            "repo_files_deleted": cleanup.repo_files_deleted,
            "hashes_rewritten": cleanup.hashes_rewritten,
            "final_result_status_changed": cleanup.final_result_status_changed,
            "created_at": cleanup.created_at,
        }
        write_json_artifact(
            run_dir / "cleanup_validation.json",
            validation_data,
        )
        
        # Write run manifest
        run_manifest = RunManifest(
            run_id=cleanup.run_id,
            phase="cleanup_retention",
            status="completed",
            artifact_path=str(run_dir / "cleanup_report.json"),
            created_at=cleanup.created_at,
            metadata={
                "cleanup_files": [
                    "cleanup_report.json",
                    "cleanup_validation.json",
                    "artifact_index.json",
                    "run_manifest.json",
                ]
            },
        )
        write_json_artifact(run_dir / "run_manifest.json", run_manifest.to_dict())
        
        # Compute hashes and write artifact index
        artifact_list = [
            "cleanup_report.json",
            "cleanup_validation.json",
            "run_manifest.json",
        ]
        artifact_hashes = compute_artifact_hashes(artifact_list)
        artifact_index = create_artifact_index(artifact_list)
        artifact_index["run_id"] = cleanup.run_id
        artifact_index["phase"] = "cleanup_retention"
        artifact_index["hashes"] = artifact_hashes
        write_json_artifact(run_dir / "artifact_index.json", artifact_index)
        
        # Write latest pointer (pointer-only)
        latest_pointer = LatestPointer(
            latest_run_id=cleanup.run_id,
            latest_phase="cleanup_retention",
            latest_artifact=str(run_dir / "cleanup_report.json"),
            created_at=cleanup.created_at,
        )
        write_json_artifact(output_root / "latest.json", latest_pointer.to_dict())
        
        return 0
    except OSError as e:
        print(f"ERROR: Cannot write cleanup output: {e}")
        return 1
