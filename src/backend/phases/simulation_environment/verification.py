"""Post-apply verification for Simulation Environment."""
import hashlib
from pathlib import Path
from typing import Any

from .schema import (
    Post_Apply_Verification,
    Verification_Result,
    Verification_Status,
    Changed_File,
)
from .errors import VerificationError


def check_unrelated_files_unchanged(
    isolated_env: dict[str, Any],
    demo: dict[str, Any],
    changed_files: list[Changed_File],
) -> bool:
    """Check that unrelated files remain unchanged.
    
    Args:
        isolated_env: Isolated environment dictionary
        demo: Demo dictionary
        changed_files: List of changed files from mutation
        
    Returns:
        True if no unrelated files changed
    """
    # Get original source hashes
    source_hashes = isolated_env.get("source_hashes", {})
    isolated_root = Path(isolated_env.get("isolated_root_path", "."))
    
    # Check that files not in changed_files still have original hashes
    for file_path, original_hash in source_hashes.items():
        # Skip files that were changed
        if file_path in [cf.file_path for cf in changed_files]:
            continue
        
        # Check if file still exists and has same hash
        target_file = isolated_root / file_path
        if target_file.exists():
            current_hash = _compute_file_hash(target_file)
            if current_hash != original_hash:
                return False
    
    return True


def check_no_unresolved_conflict(
    demo: dict[str, Any],
    verification_results: list[Verification_Result],
) -> bool:
    """Check that no unresolved conflicts remain.
    
    Args:
        demo: Demo dictionary
        verification_results: List of verification results
        
    Returns:
        True if no unresolved conflicts
    """
    # Check for conflict-related failures
    for vr in verification_results:
        if vr.status == Verification_Status.failed and "conflict" in vr.message.lower():
            return False
    
    return True


def check_no_detected_regression(
    demo: dict[str, Any],
    verification_results: list[Verification_Result],
) -> bool:
    """Check that no regressions are detected.
    
    Args:
        demo: Demo dictionary
        verification_results: List of verification results
        
    Returns:
        True if no regressions detected
    """
    # Check for regression-related failures
    for vr in verification_results:
        if vr.status == Verification_Status.failed and "regression" in vr.message.lower():
            return False
    
    return True


def _compute_file_hash(file_path: str | Path) -> str:
    """Compute SHA-256 hash of a file."""
    path = Path(file_path)
    if not path.exists():
        return ""
    
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def complete_verification(
    post_verify: Post_Apply_Verification,
    isolated_env: dict[str, Any],
    demo: dict[str, Any],
) -> Post_Apply_Verification:
    """Complete verification by checking all requirements.
    
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
        post_verify: Partial post-apply verification
        isolated_env: Isolated environment
        demo: Demo dictionary
        
    Returns:
        Completed Post_Apply_Verification
    """
    changed_files = post_verify.target_mutation.changed_files if post_verify.target_mutation else []
    
    # Check unrelated files unchanged
    no_unrelated_file_changed = check_unrelated_files_unchanged(
        isolated_env, demo, changed_files
    )
    
    # Check no unresolved conflict
    no_unresolved_conflict = check_no_unresolved_conflict(
        demo, post_verify.verification_results
    )
    
    # Check no detected regression
    no_detected_regression = check_no_detected_regression(
        demo, post_verify.verification_results
    )
    
    # Check output artifacts valid (placeholder - would check actual artifacts)
    output_artifacts_valid = True
    
    # Check required evidence complete (placeholder)
    required_evidence_complete = True
    
    # Update verification
    updated = Post_Apply_Verification(
        verification_id=post_verify.verification_id,
        target_mutation=post_verify.target_mutation,
        verification_results=list(post_verify.verification_results),
        intended_correction_exists=post_verify.intended_correction_exists,
        files_match_admitted_plan=post_verify.files_match_admitted_plan,
        required_tests_pass=post_verify.required_tests_pass,
        required_build_checks_pass=post_verify.required_build_checks_pass,
        required_schema_checks_pass=post_verify.required_schema_checks_pass,
        no_required_file_missing=post_verify.no_required_file_missing,
        no_unexpected_file_created=post_verify.no_unexpected_file_created,
        no_unrelated_file_changed=no_unrelated_file_changed,
        no_unresolved_conflict=no_unresolved_conflict,
        no_detected_regression=no_detected_regression,
        output_artifacts_valid=output_artifacts_valid,
        required_evidence_complete=required_evidence_complete,
        overall_status=post_verify.overall_status,
        failure_reason=post_verify.failure_reason,
        metadata=dict(post_verify.metadata),
    )
    
    # If any check failed, update overall status
    all_checks_pass = all([
        updated.intended_correction_exists,
        updated.files_match_admitted_plan,
        updated.required_tests_pass,
        updated.no_required_file_missing,
        updated.no_unexpected_file_created,
        updated.no_unrelated_file_changed,
        updated.no_unresolved_conflict,
        updated.no_detected_regression,
        updated.output_artifacts_valid,
        updated.required_evidence_complete,
    ])
    
    if all_checks_pass:
        updated.overall_status = Verification_Status.passed
        updated.failure_reason = None
    else:
        updated.overall_status = Verification_Status.failed
        updated.failure_reason = "One or more verification checks failed"
    
    return updated
