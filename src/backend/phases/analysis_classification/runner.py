"""
Analysis_Classification runner.

Canonical entry point: run_analysis_classification.
"""
from pathlib import Path
from typing import Any

from backend.phases.analysis_classification.schema import (
    Analysis_Classification_Input,
    Analysis_Classification_Output,
)
from backend.phases.analysis_classification.errors import (
    Analysis_Classification_Admission_Error,
)
from backend.phases.analysis_classification.validator import validate_admission
from backend.phases.analysis_classification.normalizer import normalize_scan_output
from backend.phases.analysis_classification.classifier import (
    classify_request_kind,
    classify_items,
)
from backend.phases.analysis_classification.grouping import build_groups
from backend.phases.analysis_classification.fingerprint import (
    compute_analysis_classification_id,
    compute_analysis_classification_fingerprint,
)
from backend.phases.analysis_classification.artifact import (
    write_analysis_classification_artifact,
)


def _scan_output_to_dict(scan_output: Any) -> dict[str, Any]:
    if hasattr(scan_output, "to_dict"):
        return scan_output.to_dict()
    if isinstance(scan_output, dict):
        return dict(scan_output)
    raise Analysis_Classification_Admission_Error("scan_output is not a dict or Scan_Output")


def _input_to_object(input_data: Any) -> Analysis_Classification_Input:
    """Normalize input to Analysis_Classification_Input if needed."""
    if isinstance(input_data, Analysis_Classification_Input):
        return input_data

    if not isinstance(input_data, dict):
        raise Analysis_Classification_Admission_Error("input_data must be a dict or Analysis_Classification_Input")

    return Analysis_Classification_Input(
        request_id=input_data["request_id"],
        request_text=input_data["request_text"],
        scan_output=input_data["scan_output"],
        request_metadata=input_data.get("request_metadata", {}),
        dossier_evidence_refs=input_data.get("dossier_evidence_refs", []),
        metadata=input_data.get("metadata", {}),
    )


def run_analysis_classification(
    input_data: Analysis_Classification_Input | dict[str, Any],
    output_root: str | Path | None = None,
) -> Analysis_Classification_Output:
    """Run the Analysis_Classification phase.

    Args:
        input_data: Analysis_Classification_Input object or dict.
        output_root: Optional output directory for the artifact.

    Returns:
        Analysis_Classification_Output.

    Raises:
        Analysis_Classification_Admission_Error: If input is structurally invalid.
    """
    # Admission validation
    validate_admission(input_data)

    input_obj = _input_to_object(input_data)
    scan_dict = _scan_output_to_dict(input_obj.scan_output)

    request_kind = classify_request_kind(input_obj.request_text)

    # Normalize every Scan-detected source record.
    # Caller-owned extension records (duplicate/drift) are read from input metadata.
    items = normalize_scan_output(input_obj.scan_output, input_obj)

    # Classify every item
    decisions, notices = classify_items(items, request_kind)

    # Build duplicate/drift groups from Scan evidence
    groups = build_groups(items, decisions)

    # Coverage accounting
    detected_source_count = len(items)
    normalized_item_count = len(items)
    classification_count = len(decisions)

    classified_source_ids = [item.source_item_id for item in items]
    unclassified_source_ids: list[str] = []
    duplicate_source_ids = [
        item.source_item_id
        for item in items
        if item.source_kind == "duplicate_group"
    ]

    actionable_count = sum(1 for d in decisions if d.actionable)
    non_actionable_count = classification_count - actionable_count
    needs_review_count = sum(1 for d in decisions if d.recommended_action == "needs_review")

    duplicate_group_count = sum(1 for g in groups if g.group_type.startswith("duplicate_"))
    drift_group_count = sum(1 for g in groups if g.group_type.endswith("_drift"))

    user_choice_required = any(
        d.recommended_action == "needs_review" or len(d.allowed_actions) > 1
        for d in decisions
        if d.actionable
    )

    analysis_classification_id = compute_analysis_classification_id(
        input_obj.request_id,
        request_kind,
        scan_dict["scan_fingerprint"],
    )

    output = Analysis_Classification_Output(
        phase="analysis_classification",
        status="completed",
        analysis_classification_id=analysis_classification_id,
        request_id=input_obj.request_id,
        request_kind=request_kind,
        source_phase=scan_dict["phase"],
        source_status=scan_dict["status"],
        snapshot_fingerprint=scan_dict["snapshot_fingerprint"],
        scan_fingerprint=scan_dict["scan_fingerprint"],
        target_root=scan_dict["target_root"],
        detected_source_count=detected_source_count,
        normalized_item_count=normalized_item_count,
        classification_count=classification_count,
        actionable_count=actionable_count,
        non_actionable_count=non_actionable_count,
        needs_review_count=needs_review_count,
        duplicate_group_count=duplicate_group_count,
        drift_group_count=drift_group_count,
        items=items,
        decisions=decisions,
        groups=groups,
        notices=notices,
        classified_source_ids=classified_source_ids,
        unclassified_source_ids=unclassified_source_ids,
        duplicate_source_ids=duplicate_source_ids,
        coverage_complete=True,
        classification_complete=True,
        user_choice_required=user_choice_required,
        dossier_evidence_refs=input_obj.dossier_evidence_refs,
        next_route="statement_output",
    )

    output.analysis_classification_fingerprint = compute_analysis_classification_fingerprint(output)

    if output_root is not None:
        write_analysis_classification_artifact(output_root, output.to_dict())

    return output


def main(args: list[str] | None = None) -> int:
    """CLI entry point for analysis_classification phase.
    
    Args:
        args: Command line arguments (defaults to sys.argv).
        
    Returns:
        Exit code (0 for success, 1 for error).
    """
    import argparse
    import json
    from pathlib import Path
    
    parser = argparse.ArgumentParser(
        prog="analysis_classification",
        description="Analysis and classification phase"
    )
    parser.add_argument(
        "scan_path",
        help="Path to scan artifact"
    )
    parser.add_argument(
        "--output-root",
        required=True,
        help="Output directory for artifacts"
    )
    
    parsed = parser.parse_args(args)
    
    try:
        # Load scan output
        with open(parsed.scan_path, 'r', encoding='utf-8') as f:
            scan_data = json.load(f)
        
        # Create input for analysis classification
        input_data = Analysis_Classification_Input(
            request_id="cli-req-001",
            request_text="CLI analysis classification",
            scan_output=scan_data,
            request_metadata={"origin": "cli"},
            dossier_evidence_refs=[],
            metadata={}
        )
        
        result = run_analysis_classification(input_data, parsed.output_root)
        print(f"Analysis classification completed: {parsed.scan_path}")
        print(f"  Status: {result.status}")
        print(f"  Detected sources: {result.detected_source_count}")
        print(f"  Output: {Path(parsed.output_root) / '03_analysis_classification.json'}")
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1