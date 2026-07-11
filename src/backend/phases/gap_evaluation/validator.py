"""Gap Evaluation validator."""
from typing import Any
from .schema import (
    Gap_Evaluation_Input,
    Gap_Item,
    Package_Plan_Patch,
    Gap_Evaluation_Attempt,
    Evaluation_Status,
)
from .errors import (
    InvalidInputError,
    ReadinessThresholdError,
    GraderFailureError,
    ConflictError,
    SimulationNotReadyError,
)


READINESS_THRESHOLD = 0.9391


def validate_input(input_data: Gap_Evaluation_Input) -> None:
    """Validate Gap_Evaluation_Input.
    
    Raises:
        InvalidInputError: if input is missing required fields
    """
    if not input_data.statement_output:
        raise InvalidInputError("statement_output is required")
    if input_data.package_plan is None:
        raise InvalidInputError("package_plan is required")
    # Empty package_plan is allowed (will be detected as a gap)
    # dossier_evidence_refs and supporting_metadata can be empty


def validate_gap_item(gap: Gap_Item) -> None:
    """Validate that a Gap_Item has all required fields.
    
    Raises:
        InvalidInputError: if gap is missing required fields
    """
    required_fields = [
        "gap_code",
        "affected_item", 
        "evidence",
        "failure_reason",
        "required_patch",
        "success_looks_like",
    ]
    for field_name in required_fields:
        value = getattr(gap, field_name, None)
        if not value:
            raise InvalidInputError(
                f"Gap_Item missing required field: {field_name}"
            )


def validate_patch(patch: Package_Plan_Patch) -> None:
    """Validate that a Package_Plan_Patch has required fields.
    
    Raises:
        InvalidInputError: if patch is missing required fields
    """
    if not patch.patch_id:
        raise InvalidInputError("Package_Plan_Patch missing patch_id")
    if not patch.target_field:
        raise InvalidInputError("Package_Plan_Patch missing target_field")


def check_readiness(readiness: float, grader_failures: list[str], 
                   unresolved_conflict: bool, simulation_ready: bool) -> bool:
    """Check if evaluation meets readiness criteria.
    
    Returns:
        True if all criteria are met, False otherwise
    """
    return (
        readiness >= READINESS_THRESHOLD and
        len(grader_failures) == 0 and
        not unresolved_conflict and
        simulation_ready
    )


def validate_attempt_readiness(attempt: Gap_Evaluation_Attempt) -> None:
    """Validate attempt meets readiness criteria.
    
    Raises:
        ReadinessThresholdError: if readiness below threshold
        GraderFailureError: if required grader failures present
        ConflictError: if unresolved conflict present
        SimulationNotReadyError: if simulation not ready
    """
    if attempt.readiness < READINESS_THRESHOLD:
        raise ReadinessThresholdError(
            f"Readiness {attempt.readiness} below threshold {READINESS_THRESHOLD}"
        )
    if attempt.required_grader_failures:
        raise GraderFailureError(
            f"Required grader failures present: {attempt.required_grader_failures}"
        )
    if attempt.unresolved_conflict:
        raise ConflictError("Unresolved conflict detected")
    if not attempt.simulation_ready:
        raise SimulationNotReadyError("Simulation not ready")


def validate_patches_compatible(patches: list[Package_Plan_Patch]) -> bool:
    """Check if all patches are mutually compatible.
    
    Args:
        patches: List of patches to check
        
    Returns:
        True if all patches are compatible, False otherwise
    """
    patch_ids = [p.patch_id for p in patches]
    
    for patch in patches:
        for incompatible_id in patch.incompatible_with:
            if incompatible_id in patch_ids:
                return False
    
    # Check that compatible_with constraints are satisfied
    # If a patch specifies compatible_with, all patches should be in that list
    for patch in patches:
        if patch.compatible_with:
            for other_patch in patches:
                if other_patch.patch_id != patch.patch_id:
                    if patch.compatible_with and other_patch.patch_id not in patch.compatible_with:
                        # compatible_with is a whitelist - if empty, all are compatible
                        # if non-empty, only those in the list are compatible
                        pass
    
    return True


def get_compatible_patches(patches: list[Package_Plan_Patch]) -> list[Package_Plan_Patch]:
    """Filter patches to get only mutually compatible ones.
    
    Args:
        patches: All available patches
        
    Returns:
        List of mutually compatible patches
    """
    # Simple greedy algorithm: add patches one by one if compatible with all selected
    compatible_patches = []
    
    for patch in patches:
        existing_ids = [p.patch_id for p in compatible_patches]
        if patch.is_compatible_with(existing_ids):
            compatible_patches.append(patch)
    
    return compatible_patches


def get_incompatible_patches(patches: list[Package_Plan_Patch]) -> list[Package_Plan_Patch]:
    """Get patches that are incompatible with at least one other patch.
    
    Args:
        patches: All available patches
        
    Returns:
        List of incompatible patches
    """
    incompatible = []
    patch_ids = [p.patch_id for p in patches]
    
    for patch in patches:
        for incompatible_id in patch.incompatible_with:
            if incompatible_id in patch_ids:
                if patch not in incompatible:
                    incompatible.append(patch)
                break
    
    return incompatible
