"""Cleanup/Retention schema definitions."""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CleanupRetention:
    """Cleanup/Retention report schema."""
    run_id: str
    output_root: str
    dry_run: bool
    confirm_cleanup: bool
    cleanup_status: str
    preserved_artifacts: list[str]
    deleted_paths: list[str]
    skipped_paths: list[str]
    blocked_paths: list[str]
    cleanup_errors: list[str]
    proof_artifacts_preserved: bool
    latest_pointer_preserved: bool
    artifact_index_preserved: bool
    run_manifest_preserved: bool
    final_result_artifact_preserved: bool
    created_at: str
    target_mutation_performed: bool = False
    repo_files_deleted: bool = False
    hashes_rewritten: bool = False
    final_result_status_changed: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "output_root": self.output_root,
            "dry_run": self.dry_run,
            "confirm_cleanup": self.confirm_cleanup,
            "cleanup_status": self.cleanup_status,
            "preserved_artifacts": self.preserved_artifacts,
            "deleted_paths": self.deleted_paths,
            "skipped_paths": self.skipped_paths,
            "blocked_paths": self.blocked_paths,
            "cleanup_errors": self.cleanup_errors,
            "proof_artifacts_preserved": self.proof_artifacts_preserved,
            "latest_pointer_preserved": self.latest_pointer_preserved,
            "artifact_index_preserved": self.artifact_index_preserved,
            "run_manifest_preserved": self.run_manifest_preserved,
            "final_result_artifact_preserved": self.final_result_artifact_preserved,
            "created_at": self.created_at,
            "target_mutation_performed": self.target_mutation_performed,
            "repo_files_deleted": self.repo_files_deleted,
            "hashes_rewritten": self.hashes_rewritten,
            "final_result_status_changed": self.final_result_status_changed,
            "metadata": self.metadata,
        }
