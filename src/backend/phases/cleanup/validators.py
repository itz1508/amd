"""Cleanup Retention validators - identify preserved vs transient artifacts."""
import json
import os
from pathlib import Path
from typing import Any


# Artifacts that must NEVER be deleted
PRESERVED_ARTIFACT_PATTERNS = {
    # Phase 09 artifacts
    "09_final_result_locked.json",
    "09_final_result_validation.json",
    # Phase 08 artifacts
    "08_post_apply_verification.json",
    # Phase 07 artifacts
    "07_user_apply_gate.json",
    "07_user_apply_mutation_result.json",
    # Phase 06 artifacts
    "06_apply_mutation_boundary.json",
    "06_apply_mutation_boundary_packet.json",
    "06_apply_mutation_authorization_packet.json",
    # Phase 05 artifacts
    "05_authority_review.json",
    # Phase 04 artifacts
    "04_replay_record.json",
    "04_replay_input_packet.json",
    # Phase 03 artifacts
    "03_replay_input_candidate.json",
    "03_sandbox_result_review.json",
    "03_sandbox_simulation_result.json",
    "03_runtime_foundation.json",
    # Phase 02 artifacts
    "02_analysis_handoff.json",
    "02_handoff_statement.json",
    "02_llm_statement.json",
    "02_raw_statement.json",
    # Phase 01 artifacts
    "01_scan_snapshot.json",
    # Manifest and index files
    "run_manifest.json",
    "artifact_index.json",
    # Pointer
    "latest.json",
    # Cleanup artifacts
    "cleanup_report.json",
    "cleanup_validation.json",
}

# Files that are safe to delete (transient runtime material)
TRANSIENT_PATTERNS = {
    "edge_runtime_",  # Sandbox runtime workspaces
    "venv",  # Virtual environments
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".egg-info",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.egg",
    "*.egg-info",
    "*.whl",
    "*.tmp",
    "*.temp",
    "temp_",
    "scratch_",
}


def is_preserved_artifact(file_path: Path) -> bool:
    """Check if a file is a preserved artifact that must not be deleted."""
    file_name = file_path.name
    
    # Check if it's in the preserved list
    if file_name in PRESERVED_ARTIFACT_PATTERNS:
        return True
    
    # Check if it's a manifest, index, or pointer file in any run directory
    if file_name in {"run_manifest.json", "artifact_index.json", "latest.json"}:
        return True
    
    # Check if it's a cleanup artifact
    if file_name.startswith("cleanup_") and file_name.endswith(".json"):
        return True
    
    return False


def is_transient_path(path: Path) -> bool:
    """Check if a path is transient (safe to delete)."""
    path_str = str(path)
    
    # Check for transient patterns
    for pattern in TRANSIENT_PATTERNS:
        if pattern in path_str:
            return True
    
    # Check if it's a directory that looks like transient runtime
    if path.is_dir():
        dir_name = path.name.lower()
        if any(pattern in dir_name for pattern in ["edge_runtime", "venv", ".venv", "__pycache__"]):
            return True
    
    return False


def is_under_output_root(path: Path, output_root: Path) -> bool:
    """Check if a path is under the output root."""
    try:
        path.resolve().relative_to(output_root.resolve())
        return True
    except ValueError:
        return False


def is_repo_file(path: Path, repo_root: Path) -> bool:
    """Check if a path is under the repo root."""
    try:
        path.resolve().relative_to(repo_root.resolve())
        return True
    except ValueError:
        return False


def validate_cleanup_safety(
    path: Path,
    output_root: Path,
    repo_root: Path | None = None,
) -> tuple[bool, str]:
    """Validate that a path is safe to consider for cleanup.
    
    Returns (is_safe, reason). A path is safe to consider if:
    - It's under output_root
    - It's NOT a preserved artifact
    - It's NOT under repo_root (unless repo_root == output_root)
    """
    # If it's a preserved artifact, never safe to delete
    if is_preserved_artifact(path):
        return False, "Preserved artifact - must not be deleted"
    
    # Check if under output root
    if not is_under_output_root(path, output_root):
        return False, "Outside output root - not allowed"
    
    # If repo root is provided and different from output root, check we're not in repo
    if repo_root and repo_root != output_root:
        if is_repo_file(path, repo_root):
            return False, "In repo root - not allowed"
    
    return True, "Safe to consider for cleanup"


def get_preserved_artifacts(output_root: Path) -> list[Path]:
    """Get list of all preserved artifacts in the output root."""
    preserved = []
    
    # Walk through all runs directories
    runs_dir = output_root / "runs"
    if runs_dir.exists():
        for run_dir in runs_dir.iterdir():
            if run_dir.is_dir():
                for artifact_pattern in PRESERVED_ARTIFACT_PATTERNS:
                    artifact_path = run_dir / artifact_pattern
                    if artifact_path.exists():
                        preserved.append(artifact_path)
                
                # Also check for manifest and index in each run
                for required_file in ["run_manifest.json", "artifact_index.json"]:
                    file_path = run_dir / required_file
                    if file_path.exists():
                        preserved.append(file_path)
    
    # Check root level files
    for root_file in ["latest.json", "cleanup_report.json", "cleanup_validation.json"]:
        file_path = output_root / root_file
        if file_path.exists():
            preserved.append(file_path)
    
    return preserved


def find_transient_paths(output_root: Path) -> list[Path]:
    """Find all transient paths under output root that are safe to clean up."""
    transient_paths = []
    
    # Look for transient directories and files
    for item in output_root.rglob("*"):
        if is_preserved_artifact(item):
            continue
        if is_transient_path(item):
            transient_paths.append(item)
    
    return transient_paths
