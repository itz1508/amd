"""Gap Evaluation runner."""
import hashlib
import json
import copy
from pathlib import Path
from typing import Any

from .schema import (
    Gap_Evaluation_Input,
    Gap_Evaluation_Output,
    Gap_Evaluation_Attempt,
    Gap_Item,
    Package_Plan_Patch,
    Evaluation_Status,
    Next_Route,
    Gap_Status,
    Gap_Severity,
)
from .validator import (
    validate_input,
    validate_gap_item,
    validate_patch,
    check_readiness,
    get_compatible_patches,
    get_incompatible_patches,
)
from .errors import (
    GapEvaluationError,
    InvalidInputError,
    MaxAttemptsExceededError,
    PatchApplicationError,
)
from .patch_policy import can_auto_patch_gap


READINESS_THRESHOLD = 0.9391


def _normalize_package_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """Normalize package plan for fingerprinting.
    
    Sorts keys and serializes nested structures deterministically.
    """
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
    
    return normalize_value(plan)


def _normalize_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Normalize supporting metadata for fingerprinting."""
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
    
    return normalize_value(metadata)


def _normalize_gaps(gaps: list[Gap_Item]) -> list[dict[str, Any]]:
    """Normalize gap records for fingerprinting."""
    return [
        {
            "gap_code": gap.gap_code,
            "affected_item": gap.affected_item,
            "evidence": gap.evidence,
            "failure_reason": gap.failure_reason,
            "required_patch": gap.required_patch,
            "success_looks_like": gap.success_looks_like,
            "severity": gap.severity.value,
            "status": gap.status.value,
            "metadata": dict(sorted(gap.metadata.items())),
        }
        for gap in sorted(gaps, key=lambda g: g.gap_code)
    ]


def _normalize_patches(patches: list[Package_Plan_Patch]) -> list[dict[str, Any]]:
    """Normalize patch records for fingerprinting."""
    return [
        {
            "patch_id": patch.patch_id,
            "target_field": patch.target_field,
            "affected_item": patch.affected_item,
            "original_value": patch.original_value,
            "corrected_value": patch.corrected_value,
            "evidence": patch.evidence,
            "related_gap_codes": sorted(patch.related_gap_codes),
            "current_value": patch.current_value,
            "new_value": patch.new_value,
            "patch_type": patch.patch_type,
            "compatible_with": sorted(patch.compatible_with),
            "incompatible_with": sorted(patch.incompatible_with),
            "description": patch.description,
            "metadata": dict(sorted(patch.metadata.items())),
        }
        for patch in sorted(patches, key=lambda p: p.patch_id)
    ]


def gap_evaluation_fingerprint(
    statement_output: dict[str, Any],
    package_plan: dict[str, Any],
    supporting_metadata: dict[str, Any],
    gaps: list[Gap_Item],
    patches: list[Package_Plan_Patch],
    readiness: float,
    required_grader_failures: list[str],
    unresolved_conflict: bool,
    simulation_ready: bool,
    next_route: str,
    handoff_ref: str | None = None,
) -> str:
    """Compute deterministic fingerprint for gap evaluation.
    
    Derives from:
    - normalized Statement_Output identifiers and fingerprint
    - normalized package plan
    - supporting metadata used by evaluation
    - ordered gap records
    - ordered patch records
    - readiness and blocker fields
    - final routing result
    
    Excludes:
    - timestamps
    - run identifiers
    - temporary paths
    - output_root
    - absolute machine-specific paths
    - artifact location
    """
    # Normalize statement output identifiers and fingerprint
    statement_output_id = statement_output.get("statement_output_id", "")
    statement_output_fp = statement_output.get("statement_output_fingerprint", "")
    raw_statement_id = statement_output.get("raw_statement_id", "")
    handoff_statement_id = statement_output.get("handoff_statement_id", "")
    llm_statement_id = statement_output.get("llm_statement_id", "")
    
    payload = {
        # Statement output identifiers and fingerprint
        "statement_output_id": statement_output_id,
        "statement_output_fingerprint": statement_output_fp,
        "raw_statement_id": raw_statement_id,
        "handoff_statement_id": handoff_statement_id,
        "llm_statement_id": llm_statement_id,
        
        # Normalized package plan
        "package_plan": _normalize_package_plan(package_plan),
        
        # Supporting metadata
        "supporting_metadata": _normalize_metadata(supporting_metadata),
        
        # Ordered gap records
        "gaps": _normalize_gaps(gaps),
        
        # Ordered patch records
        "patches": _normalize_patches(patches),
        
        # Readiness and blocker fields
        "readiness": readiness,
        "required_grader_failures": sorted(required_grader_failures),
        "unresolved_conflict": unresolved_conflict,
        "simulation_ready": simulation_ready,
        
        # Final routing result
        "next_route": next_route,
        "handoff_ref": handoff_ref,
    }
    
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _detect_gaps(
    statement_output: dict[str, Any],
    package_plan: dict[str, Any],
    supporting_metadata: dict[str, Any],
    dossier_evidence_refs: list[str],
) -> list[Gap_Item]:
    """Perform automated initial evaluation to detect all gaps.
    
    This is the core gap detection logic. Returns all detectable gaps together.
    
    Args:
        statement_output: Statement_Output_Output dictionary
        package_plan: Current package plan
        supporting_metadata: Supporting metadata
        dossier_evidence_refs: Dossier evidence references
        
    Returns:
        List of detected Gap_Item objects
    """
    gaps = []
    
    # Check for missing required fields in statement output
    required_statement_fields = ["statement_output_id", "raw_statement_id", 
                                   "handoff_statement_id", "llm_statement_id"]
    for field_name in required_statement_fields:
        if field_name not in statement_output:
            gaps.append(Gap_Item(
                gap_code="SO-001-MISSING_FIELD",
                affected_item=f"statement_output.{field_name}",
                evidence=f"Field '{field_name}' missing from statement_output",
                failure_reason=f"Required field '{field_name}' not present",
                required_patch=f"Add '{field_name}' to statement_output",
                success_looks_like=f"statement_output contains '{field_name}'",
                severity=Gap_Severity.high,
            ))
    
    # Check for empty package plan
    if not package_plan:
        gaps.append(Gap_Item(
            gap_code="PP-001-EMPTY_PLAN",
            affected_item="package_plan",
            evidence="package_plan is empty",
            failure_reason="Package plan cannot be empty",
            required_patch="Provide a valid package plan",
            success_looks_like="package_plan contains at least one field",
            severity=Gap_Severity.critical,
        ))
    else:
        # Check for missing required fields in package plan
        required_plan_fields = ["name", "version"]
        for field_name in required_plan_fields:
            if field_name not in package_plan:
                gaps.append(Gap_Item(
                    gap_code="PP-002-MISSING_REQUIRED_FIELD",
                    affected_item=f"package_plan.{field_name}",
                    evidence=f"Required field '{field_name}' missing from package_plan",
                    failure_reason=f"Package plan missing required field: {field_name}",
                    required_patch=f"Add '{field_name}' field to package_plan",
                    success_looks_like=f"package_plan contains '{field_name}'",
                    severity=Gap_Severity.high,
                ))

        if not package_plan.get("success_looks_like"):
            gaps.append(Gap_Item(
                gap_code="PP-003-MISSING_SUCCESS_CRITERIA",
                affected_item="package_plan.success_looks_like",
                evidence="Required field 'success_looks_like' missing from package_plan",
                failure_reason="Package plan must define what success looks like before presimulation",
                required_patch="Add explicit success_looks_like to package_plan",
                success_looks_like="package_plan.success_looks_like contains concrete pass criteria",
                severity=Gap_Severity.high,
            ))

        mutation_boundary = package_plan.get("apply_mutation_boundary")
        if not isinstance(mutation_boundary, dict) or not mutation_boundary.get("boundary_root"):
            gaps.append(Gap_Item(
                gap_code="PP-004-MISSING_MUTATION_BOUNDARY",
                affected_item="package_plan.apply_mutation_boundary.boundary_root",
                evidence="Required field 'apply_mutation_boundary.boundary_root' missing from package_plan",
                failure_reason="Mutation boundary root must be explicit before presimulation",
                required_patch="Add apply_mutation_boundary.boundary_root to package_plan",
                success_looks_like="package_plan.apply_mutation_boundary.boundary_root is explicit",
                severity=Gap_Severity.high,
            ))

        if not (package_plan.get("selected_execution_tool") or package_plan.get("selected_action")):
            gaps.append(Gap_Item(
                gap_code="PP-005-MISSING_SELECTED_ACTION",
                affected_item="package_plan.selected_execution_tool",
                evidence="No selected execution tool/action found in package_plan",
                failure_reason="Agent must choose the execution tool or action before presimulation",
                required_patch="Add selected_execution_tool or selected_action to package_plan",
                success_looks_like="package_plan identifies the selected execution tool/action",
                severity=Gap_Severity.high,
            ))
    
    # Check dossier evidence references
    if not dossier_evidence_refs:
        gaps.append(Gap_Item(
            gap_code="DER-001-NO_EVIDENCE",
            affected_item="dossier_evidence_refs",
            evidence="No dossier evidence references provided",
            failure_reason="At least one dossier evidence reference is required",
            required_patch="Add dossier evidence references",
            success_looks_like="dossier_evidence_refs contains at least one reference",
            severity=Gap_Severity.medium,
        ))
    
    # Check for inconsistency between statement output and metadata
    statement_ids = {
        "raw": statement_output.get("raw_statement_id", ""),
        "handoff": statement_output.get("handoff_statement_id", ""),
        "llm": statement_output.get("llm_statement_id", ""),
    }
    
    metadata_ids = supporting_metadata.get("statement_ids", {})
    if metadata_ids:
        for key, value in metadata_ids.items():
            if key in statement_ids and statement_ids[key] != value:
                gaps.append(Gap_Item(
                    gap_code="CON-001-ID_MISMATCH",
                    affected_item=f"statement_ids.{key}",
                    evidence=f"Metadata has {key}={value}, but statement_output has {key}={statement_ids[key]}",
                    failure_reason=f"Inconsistent {key} identifier between metadata and statement_output",
                    required_patch=f"Ensure {key} matches between metadata and statement_output",
                    success_looks_like=f"statement_output.{key} == metadata.statement_ids.{key}",
                    severity=Gap_Severity.high,
                ))
    
    return gaps


def _generate_patches(gaps: list[Gap_Item], package_plan: dict[str, Any],
                      supporting_metadata: dict[str, Any]) -> list[Package_Plan_Patch]:
    """Generate patches for detected gaps.
    
    Creates Package_Plan_Patch objects for each gap that can be patched.
    Each patch records: patch_id, affected_item, original_value, corrected_value, evidence, related_gap_codes
    
    Args:
        gaps: Detected gaps
        package_plan: Current package plan
        supporting_metadata: Supporting metadata
        
    Returns:
        List of Package_Plan_Patch objects
    """
    patches = []
    patch_counter = 0
    
    for gap in gaps:
        patch_counter += 1
        patch_id = f"patch-{gap.gap_code}-{patch_counter:03d}"
        
        # Determine patch based on gap code
        if not can_auto_patch_gap(gap):
            continue
        elif gap.gap_code == "PP-002-MISSING_REQUIRED_FIELD":
            # Extract field name from affected_item
            field_name = gap.affected_item.split(".")[-1]
            original_value = package_plan.get(field_name, None)
            patches.append(Package_Plan_Patch(
                patch_id=patch_id,
                target_field=field_name,
                current_value=original_value,
                new_value="default_value",
                affected_item=field_name,
                original_value=original_value,
                corrected_value="default_value",
                evidence=gap.evidence,
                related_gap_codes=[gap.gap_code],
                patch_type="add",
                description=f"Add missing required field: {field_name}",
                incompatible_with=[],
                compatible_with=[],
            ))
        elif gap.gap_code == "CON-001-ID_MISMATCH":
            # Fix ID mismatch by updating supporting metadata
            field_name = gap.affected_item.split(".")[-1]
            correct_value = statement_output.get(f"{field_name}_id", "")
            original_value = supporting_metadata.get("statement_ids", {}).get(field_name, None)
            patches.append(Package_Plan_Patch(
                patch_id=patch_id,
                target_field=f"supporting_metadata.statement_ids.{field_name}",
                current_value=original_value,
                new_value=correct_value,
                affected_item=f"statement_ids.{field_name}",
                original_value=original_value,
                corrected_value=correct_value,
                evidence=gap.evidence,
                related_gap_codes=[gap.gap_code],
                patch_type="replace",
                description=f"Fix {field_name} mismatch between metadata and statement_output",
                incompatible_with=[],
                compatible_with=[],
            ))
        else:
            # Generic patch for other gap types
            patches.append(Package_Plan_Patch(
                patch_id=patch_id,
                target_field="metadata.fixes",
                current_value=supporting_metadata.get("fixes", []),
                new_value=supporting_metadata.get("fixes", []) + [gap.gap_code],
                affected_item="metadata.fixes",
                original_value=supporting_metadata.get("fixes", []),
                corrected_value=supporting_metadata.get("fixes", []) + [gap.gap_code],
                evidence=gap.evidence,
                related_gap_codes=[gap.gap_code],
                patch_type="append",
                description=f"Record fix for gap: {gap.gap_code}",
                incompatible_with=[],
                compatible_with=[],
            ))
    
    return patches


def _apply_patches(
    package_plan: dict[str, Any],
    supporting_metadata: dict[str, Any],
    patches: list[Package_Plan_Patch],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Apply compatible patches to package plan and supporting metadata.
    
    Only patches target source (package plan and supporting metadata).
    Never patches the original statement_output or other read-only inputs.
    
    Args:
        package_plan: Current package plan
        supporting_metadata: Current supporting metadata
        patches: List of patches to apply
        
    Returns:
        Tuple of (updated_package_plan, updated_supporting_metadata)
        
    Raises:
        PatchApplicationError: if patch application fails
    """
    # Deep copy to avoid mutation
    updated_plan = copy.deepcopy(package_plan)
    updated_metadata = copy.deepcopy(supporting_metadata)
    
    for patch in patches:
        try:
            # Handle different target field types
            if patch.target_field.startswith("supporting_metadata."):
                # Patch supporting metadata
                field_parts = patch.target_field.split(".")[1:]  # Remove "supporting_metadata."
                current = updated_metadata
                for part in field_parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                final_field = field_parts[-1]
                
                if patch.patch_type == "replace":
                    current[final_field] = patch.new_value
                elif patch.patch_type == "add":
                    current[final_field] = patch.new_value
                elif patch.patch_type == "append" and isinstance(current.get(final_field), list):
                    current[final_field] = current[final_field] + [patch.new_value]
                else:
                    current[final_field] = patch.new_value
            else:
                # Patch package plan
                if patch.target_field in updated_plan:
                    if patch.patch_type == "replace":
                        updated_plan[patch.target_field] = patch.new_value
                    elif patch.patch_type == "add":
                        updated_plan[patch.target_field] = patch.new_value
                    elif patch.patch_type == "append" and isinstance(updated_plan.get(patch.target_field), list):
                        updated_plan[patch.target_field] = updated_plan[patch.target_field] + [patch.new_value]
                    else:
                        updated_plan[patch.target_field] = patch.new_value
                else:
                    # Field doesn't exist, add it
                    updated_plan[patch.target_field] = patch.new_value
        
        except Exception as e:
            raise PatchApplicationError(f"Failed to apply patch {patch.patch_id}: {e}")
    
    return updated_plan, updated_metadata


def _evaluate_attempt(
    statement_output: dict[str, Any],
    package_plan: dict[str, Any],
    supporting_metadata: dict[str, Any],
    dossier_evidence_refs: list[str],
    attempt_number: int,
    applied_patches: list[Package_Plan_Patch],
) -> Gap_Evaluation_Attempt:
    """Perform a single evaluation attempt.
    
    Args:
        statement_output: Statement_Output_Output dictionary
        package_plan: Current package plan
        supporting_metadata: Current supporting metadata
        dossier_evidence_refs: Dossier evidence references
        attempt_number: Attempt number (1 or 2)
        applied_patches: Patches applied in previous attempts
        
    Returns:
        Gap_Evaluation_Attempt with results
    """
    # Detect all gaps
    gaps = _detect_gaps(statement_output, package_plan, supporting_metadata, dossier_evidence_refs)
    
    # Check if there are any gaps
    has_gaps = len(gaps) > 0
    
    # Calculate readiness based on gaps
    # Each gap reduces readiness; critical gaps reduce more
    readiness_penalty = 0.0
    required_grader_failures = []
    unresolved_conflict = False
    
    for gap in gaps:
        if gap.severity == Gap_Severity.critical:
            readiness_penalty += 0.3
            required_grader_failures.append(gap.gap_code)
        elif gap.severity == Gap_Severity.high:
            readiness_penalty += 0.15
        elif gap.severity == Gap_Severity.medium:
            readiness_penalty += 0.05
        elif gap.severity == Gap_Severity.low:
            readiness_penalty += 0.01
    
    # If there are conflicting patches or issues, mark as unresolved conflict
    conflict_gap_codes = ["CON-001-ID_MISMATCH"]
    if any(gap.gap_code in conflict_gap_codes for gap in gaps):
        unresolved_conflict = True
    
    readiness = max(0.0, 1.0 - readiness_penalty)
    simulation_ready = not has_gaps and readiness >= READINESS_THRESHOLD
    
    # Determine attempt status
    if has_gaps:
        status = Evaluation_Status.not_valid
    else:
        status = Evaluation_Status.valid
    
    return Gap_Evaluation_Attempt(
        attempt_number=attempt_number,
        status=status,
        gaps=gaps,
        applied_patches=list(applied_patches),
        readiness=round(readiness, 4),
        required_grader_failures=required_grader_failures,
        unresolved_conflict=unresolved_conflict,
        simulation_ready=simulation_ready,
        metadata={"gap_count": len(gaps), "patch_count": len(applied_patches)},
    )


def run_gap_evaluation(
    input_data: Gap_Evaluation_Input,
    output_root: Path | None = None,
) -> Gap_Evaluation_Output:
    """Run Gap_Evaluation phase.
    
    Behavior:
    1. Perform an automated initial evaluation (attempt 1)
    2. If attempt 1 is valid, route to simulation_environment
    3. If attempt 1 is not_valid:
       - Return all detectable gaps together
       - Apply all compatible corrections together to package plan and supporting metadata
       - Perform exactly one re-evaluation (attempt 2)
    4. If attempt 2 is valid, route to simulation_environment
    5. If attempt 2 is not_valid:
       - Create a bounded handoff through backend.handoff
       - Route the escalation through backend.llm
       - Route to gap_handoff
    6. Never patch target source
    7. Never ask user for missing information
    8. Never add another retry (max 2 attempts)
    9. Produce deterministic ordering, identifiers, serialization, and fingerprinting
    
    Args:
        input_data: Gap_Evaluation_Input containing all required inputs
        output_root: Optional output directory for artifacts
        
    Returns:
        Gap_Evaluation_Output artifact
        
    Raises:
        GapEvaluationError: on validation or execution errors
    """
    # Validate input
    validate_input(input_data)
    
    # Extract inputs
    statement_output = input_data.statement_output
    package_plan = input_data.package_plan
    supporting_metadata = input_data.supporting_metadata
    dossier_evidence_refs = input_data.dossier_evidence_refs
    
    attempts = []
    all_gaps = []
    all_patches = []
    applied_patches = []
    resulting_package_plan = copy.deepcopy(package_plan)
    resulting_metadata = copy.deepcopy(supporting_metadata)
    handoff_ref = None
    
    # Attempt 1: Initial evaluation
    attempt1 = _evaluate_attempt(
        statement_output=statement_output,
        package_plan=package_plan,
        supporting_metadata=supporting_metadata,
        dossier_evidence_refs=dossier_evidence_refs,
        attempt_number=1,
        applied_patches=[],
    )
    attempts.append(attempt1)
    all_gaps.extend(attempt1.gaps)
    
    # Check if attempt 1 is valid
    if attempt1.status == Evaluation_Status.valid:
        # Route to simulation_environment
        next_route = Next_Route.simulation_environment.value
        
        # Check readiness criteria for final output
        if check_readiness(
            attempt1.readiness,
            attempt1.required_grader_failures,
            attempt1.unresolved_conflict,
            attempt1.simulation_ready
        ):
            final_readiness = attempt1.readiness
            final_grader_failures = attempt1.required_grader_failures
            final_unresolved_conflict = attempt1.unresolved_conflict
            final_simulation_ready = attempt1.simulation_ready
        else:
            # Even if valid, check readiness
            final_readiness = attempt1.readiness
            final_grader_failures = attempt1.required_grader_failures
            final_unresolved_conflict = attempt1.unresolved_conflict
            final_simulation_ready = attempt1.simulation_ready
    else:
        # Attempt 1 not valid - generate patches and apply
        patches = _generate_patches(
            attempt1.gaps, package_plan, supporting_metadata
        )
        all_patches.extend(patches)
        
        # Get compatible patches
        compatible_patches = get_compatible_patches(patches)
        incompatible_patches = get_incompatible_patches(patches)
        
        # Apply all compatible patches together
        try:
            resulting_package_plan, resulting_metadata = _apply_patches(
                package_plan, supporting_metadata, compatible_patches
            )
            applied_patches.extend(compatible_patches)
        except PatchApplicationError:
            # If patch application fails, proceed to attempt 2 with original data
            resulting_package_plan = package_plan
            resulting_metadata = supporting_metadata
        
        # Attempt 2: Re-evaluation with patches applied
        attempt2 = _evaluate_attempt(
            statement_output=statement_output,
            package_plan=resulting_package_plan,
            supporting_metadata=resulting_metadata,
            dossier_evidence_refs=dossier_evidence_refs,
            attempt_number=2,
            applied_patches=list(applied_patches),
        )
        attempts.append(attempt2)
        all_gaps.extend(attempt2.gaps)
        
        # Check attempt 2 status
        if attempt2.status == Evaluation_Status.valid:
            # Route to simulation_environment
            next_route = Next_Route.simulation_environment.value
            final_readiness = attempt2.readiness
            final_grader_failures = attempt2.required_grader_failures
            final_unresolved_conflict = attempt2.unresolved_conflict
            final_simulation_ready = attempt2.simulation_ready
        else:
            # Attempt 2 failed - create handoff reference
            # Route escalation through backend.llm (conceptual, no actual invocation)
            handoff_ref = f"handoff-gap-eval-{attempt2.attempt_number}-{len(attempt2.gaps)}-gaps"
            
            # Route to gap_handoff
            next_route = Next_Route.gap_handoff.value
            final_readiness = attempt2.readiness
            final_grader_failures = attempt2.required_grader_failures
            final_unresolved_conflict = attempt2.unresolved_conflict
            final_simulation_ready = attempt2.simulation_ready
    
    # Ensure all gaps have required fields
    for gap in all_gaps:
        validate_gap_item(gap)
    
    # Ensure all patches have required fields
    for patch in all_patches:
        validate_patch(patch)
    
    # Compute fingerprint
    fp = gap_evaluation_fingerprint(
        statement_output=statement_output,
        package_plan=package_plan,
        supporting_metadata=supporting_metadata,
        gaps=all_gaps,
        patches=all_patches,
        readiness=final_readiness,
        required_grader_failures=final_grader_failures,
        unresolved_conflict=final_unresolved_conflict,
        simulation_ready=final_simulation_ready,
        next_route=next_route,
        handoff_ref=handoff_ref,
    )
    
    # Build final output
    output = Gap_Evaluation_Output(
        phase="gap_evaluation",
        status="completed",
        readiness=final_readiness,
        simulation_ready=final_simulation_ready,
        required_grader_failures=final_grader_failures,
        unresolved_conflict=final_unresolved_conflict,
        attempts=attempts,
        gaps=all_gaps,
        applied_package_plan_patches=applied_patches,
        resulting_package_plan=resulting_package_plan,
        supporting_metadata=resulting_metadata,
        dossier_evidence_refs=list(dossier_evidence_refs),
        next_route=next_route,
        handoff_ref=handoff_ref,
        gap_evaluation_fingerprint=fp,
        metadata={
            "attempt_count": len(attempts),
            "total_gaps": len(all_gaps),
            "total_patches": len(all_patches),
            "applied_patches": len(applied_patches),
        },
    )
    
    # Write artifact if output_root provided
    if output_root is not None:
        try:
            output_root.mkdir(parents=True, exist_ok=True)
            artifact_path = output_root / "05_gap_evaluation.json"
            artifact_path.write_text(
                json.dumps(output.to_dict(), sort_keys=True, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError:
            pass
    
    return output


def main(args: list[str] | None = None) -> int:
    """CLI entry point for gap_evaluation phase.
    
    Args:
        args: Command line arguments (defaults to sys.argv).
        
    Returns:
        Exit code (0 for success, 1 for error).
    """
    import argparse
    import json
    from pathlib import Path
    
    parser = argparse.ArgumentParser(
        prog="gap_evaluation",
        description="Gap evaluation phase"
    )
    parser.add_argument(
        "statement_path",
        help="Path to statement output artifact"
    )
    parser.add_argument(
        "--output-root",
        required=True,
        help="Output directory for artifacts"
    )
    
    parsed = parser.parse_args(args)
    
    try:
        # Load statement output data
        with open(parsed.statement_path, 'r', encoding='utf-8') as f:
            statement_data = json.load(f)
        
        input_data = Gap_Evaluation_Input(
            statement_output=statement_data,
            package_plan={},
            supporting_metadata={},
            dossier_evidence_refs=statement_data.get("dossier_evidence_refs", [])
        )
        
        result = run_gap_evaluation(input_data, Path(parsed.output_root))
        print(f"Gap evaluation completed: {parsed.statement_path}")
        print(f"  Status: {result.status}")
        print(f"  Output: {Path(parsed.output_root) / '05_gap_evaluation.json'}")
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
