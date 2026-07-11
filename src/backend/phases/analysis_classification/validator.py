"""
Analysis_Classification admission validator.

Rejects the complete request only when it cannot be classified structurally.
Individual Scan record problems are handled during normalization.
"""
from typing import Any

from backend.phases.analysis_classification.errors import (
    Analysis_Classification_Admission_Error,
)


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and value != ""


def _is_list_of_non_empty_strings(value: Any) -> bool:
    if not isinstance(value, list):
        return False
    return all(isinstance(item, str) and item != "" for item in value)


def validate_admission(input_data: Any) -> None:
    """Validate structural admission for Analysis_Classification_Input.

    Args:
        input_data: The Analysis_Classification_Input object or dict.

    Raises:
        Analysis_Classification_Admission_Error: If the input is structurally invalid.
    """
    if input_data is None:
        raise Analysis_Classification_Admission_Error("input_data is missing")

    # Accept dataclass instances or dicts
    if isinstance(input_data, dict):
        data = input_data
        get = data.get
    else:
        get = getattr

    request_id = get(input_data, "request_id") if not isinstance(input_data, dict) else get("request_id")
    if not _is_non_empty_string(request_id):
        raise Analysis_Classification_Admission_Error("request_id is missing or empty")

    request_text = get(input_data, "request_text") if not isinstance(input_data, dict) else get("request_text")
    if not _is_non_empty_string(request_text):
        raise Analysis_Classification_Admission_Error("request_text is missing or not a non-empty string")

    scan_output = get(input_data, "scan_output") if not isinstance(input_data, dict) else get("scan_output")
    if scan_output is None:
        raise Analysis_Classification_Admission_Error("scan_output is missing")

    # Normalize scan_output to dict for structural checks
    if hasattr(scan_output, "to_dict"):
        scan_dict = scan_output.to_dict()
    elif isinstance(scan_output, dict):
        scan_dict = scan_output
    else:
        raise Analysis_Classification_Admission_Error("scan_output is not a dict or Scan_Output")

    if scan_dict.get("phase") != "scan":
        raise Analysis_Classification_Admission_Error(
            f"scan_output.phase must be 'scan', got {scan_dict.get('phase')!r}"
        )

    if scan_dict.get("status") not in ("completed", "completed_with_notices"):
        raise Analysis_Classification_Admission_Error(
            f"scan_output.status must be 'completed' or 'completed_with_notices', got {scan_dict.get('status')!r}"
        )

    if not _is_non_empty_string(scan_dict.get("snapshot_fingerprint")):
        raise Analysis_Classification_Admission_Error("snapshot_fingerprint is missing or empty")

    if not _is_non_empty_string(scan_dict.get("scan_fingerprint")):
        raise Analysis_Classification_Admission_Error("scan_fingerprint is missing or empty")

    if not _is_non_empty_string(scan_dict.get("target_root")):
        raise Analysis_Classification_Admission_Error("target_root is missing or empty")

    files = scan_dict.get("files")
    surfaces = scan_dict.get("surfaces")
    notices = scan_dict.get("notices")

    if not isinstance(files, list):
        raise Analysis_Classification_Admission_Error("scan_output.files must be a list")
    if not isinstance(surfaces, list):
        raise Analysis_Classification_Admission_Error("scan_output.surfaces must be a list")
    if not isinstance(notices, list):
        raise Analysis_Classification_Admission_Error("scan_output.notices must be a list")

    dossier_refs = get(input_data, "dossier_evidence_refs") if not isinstance(input_data, dict) else get("dossier_evidence_refs")
    if dossier_refs is not None and not _is_list_of_non_empty_strings(dossier_refs):
        raise Analysis_Classification_Admission_Error("dossier_evidence_refs must be a list of non-empty strings")