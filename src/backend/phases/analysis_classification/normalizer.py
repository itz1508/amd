"""
Source item normalizer.

Converts every Scan-detected source record into an Analysis_Item.
Derives deterministic source_item_id from canonical content.
"""
import hashlib
import json
from typing import Any

from backend.phases.analysis_classification.schema import Analysis_Item


def _canonical_json(value: Any) -> str:
    """Return a deterministic JSON serialization for hashing."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _derive_id(prefix: str, payload: dict[str, Any]) -> str:
    """Derive a deterministic source item id."""
    canonical = _canonical_json(payload)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"{prefix}:{digest[:16]}"


def _file_payload(scan_file: Any) -> dict[str, Any]:
    if isinstance(scan_file, dict):
        return {
            "relative_path": scan_file.get("relative_path"),
            "file_type": scan_file.get("file_type"),
            "language": scan_file.get("language"),
            "category": scan_file.get("category"),
            "sha256": scan_file.get("sha256"),
        }
    return {
        "relative_path": getattr(scan_file, "relative_path", None),
        "file_type": getattr(scan_file, "file_type", None),
        "language": getattr(scan_file, "language", None),
        "category": getattr(scan_file, "category", None),
        "sha256": getattr(scan_file, "sha256", None),
    }


def _surface_payload(scan_surface: Any) -> dict[str, Any]:
    if isinstance(scan_surface, dict):
        return {
            "surface_type": scan_surface.get("surface_type"),
            "identifier": scan_surface.get("identifier"),
            "source_path": scan_surface.get("source_path"),
        }
    return {
        "surface_type": getattr(scan_surface, "surface_type", None),
        "identifier": getattr(scan_surface, "identifier", None),
        "source_path": getattr(scan_surface, "source_path", None),
    }


def _notice_payload(scan_notice: Any) -> dict[str, Any]:
    if isinstance(scan_notice, dict):
        return {
            "notice_code": scan_notice.get("notice_code"),
            "relative_path": scan_notice.get("relative_path"),
            "reason": scan_notice.get("reason"),
        }
    return {
        "notice_code": getattr(scan_notice, "notice_code", None),
        "relative_path": getattr(scan_notice, "relative_path", None),
        "reason": getattr(scan_notice, "reason", None),
    }


def _is_complete_file(payload: dict[str, Any]) -> bool:
    return bool(payload.get("relative_path")) and bool(payload.get("sha256"))


def _is_complete_surface(payload: dict[str, Any]) -> bool:
    return bool(payload.get("source_path")) and bool(payload.get("surface_type"))


def _is_complete_notice(payload: dict[str, Any]) -> bool:
    return bool(payload.get("relative_path")) and bool(payload.get("notice_code"))


def _fingerprint_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _extract_extensions(input_data: Any) -> dict[str, Any]:
    """Extract Analysis_Classification-owned extension records from input metadata.

    Supports optional future duplicate_group and drift_record records supplied
    by the caller in input.metadata.analysis_classification_extensions.
    """
    extensions: dict[str, Any] = {}
    metadata: dict[str, Any] = {}
    if isinstance(input_data, dict):
        metadata = input_data.get("metadata") or {}
    elif hasattr(input_data, "metadata"):
        metadata = getattr(input_data, "metadata") or {}
    if isinstance(metadata, dict):
        extensions = metadata.get("analysis_classification_extensions") or {}
    if not isinstance(extensions, dict):
        extensions = {}
    return extensions


def normalize_scan_output(scan_output: Any, input_data: Any | None = None) -> list[Analysis_Item]:
    """Normalize every Scan-detected source record into an Analysis_Item.

    Args:
        scan_output: Scan_Output object or dict.
        input_data: Optional Analysis_Classification_Input object or dict,
            used to read caller-supplied extension records.

    Returns:
        Sorted list of Analysis_Item instances.
    """
    if hasattr(scan_output, "to_dict"):
        scan_dict = scan_output.to_dict()
    elif isinstance(scan_output, dict):
        scan_dict = scan_output
    else:
        scan_dict = {}

    extensions = _extract_extensions(input_data)

    items: list[Analysis_Item] = []

    for scan_file in scan_dict.get("files", []):
        payload = _file_payload(scan_file)
        source_path = payload.get("relative_path")
        fingerprint = _fingerprint_payload(payload)
        if _is_complete_file(payload):
            source_item_id = _derive_id("file", payload)
            source_kind = "file"
        else:
            source_item_id = _derive_id("unreadable", payload)
            source_kind = "unreadable"
        items.append(
            Analysis_Item(
                source_item_id=source_item_id,
                source_kind=source_kind,
                source_path=source_path,
                source_fingerprint=fingerprint,
                source_payload=payload,
                source_evidence_refs=[fingerprint],
            )
        )

    for scan_surface in scan_dict.get("surfaces", []):
        payload = _surface_payload(scan_surface)
        source_path = payload.get("source_path")
        fingerprint = _fingerprint_payload(payload)
        if _is_complete_surface(payload):
            source_item_id = _derive_id("surface", payload)
            source_kind = "surface"
        else:
            source_item_id = _derive_id("unknown", payload)
            source_kind = "unknown"
        items.append(
            Analysis_Item(
                source_item_id=source_item_id,
                source_kind=source_kind,
                source_path=source_path,
                source_fingerprint=fingerprint,
                source_payload=payload,
                source_evidence_refs=[fingerprint],
            )
        )

    for scan_notice in scan_dict.get("notices", []):
        payload = _notice_payload(scan_notice)
        source_path = payload.get("relative_path")
        fingerprint = _fingerprint_payload(payload)
        if _is_complete_notice(payload):
            source_item_id = _derive_id("notice", payload)
            source_kind = "notice"
        else:
            source_item_id = _derive_id("unknown", payload)
            source_kind = "unknown"
        items.append(
            Analysis_Item(
                source_item_id=source_item_id,
                source_kind=source_kind,
                source_path=source_path,
                source_fingerprint=fingerprint,
                source_payload=payload,
                source_evidence_refs=[fingerprint],
            )
        )

    # Optional future inputs: duplicate_group and drift_record.
    # These are supported only when supplied by caller-owned extension records
    # in Analysis_Classification_Input.metadata, never by inventing evidence.
    for duplicate in extensions.get("duplicate_groups", []):
        payload = _duplicate_payload(duplicate)
        source_path = payload.get("representative_path")
        fingerprint = _fingerprint_payload(payload)
        source_item_id = _derive_id("duplicate_group", payload)
        items.append(
            Analysis_Item(
                source_item_id=source_item_id,
                source_kind="duplicate_group",
                source_path=source_path,
                source_fingerprint=fingerprint,
                source_payload=payload,
                source_evidence_refs=[fingerprint],
            )
        )

    for drift in extensions.get("drift_records", []):
        payload = _drift_payload(drift)
        source_path = payload.get("affected_path")
        fingerprint = _fingerprint_payload(payload)
        source_item_id = _derive_id("drift_record", payload)
        items.append(
            Analysis_Item(
                source_item_id=source_item_id,
                source_kind="drift_record",
                source_path=source_path,
                source_fingerprint=fingerprint,
                source_payload=payload,
                source_evidence_refs=[fingerprint],
            )
        )

    # Deterministic ordering: source_kind, source_path, source_item_id
    items.sort(key=lambda item: (item.source_kind, item.source_path or "", item.source_item_id))
    return items


def _duplicate_payload(duplicate: Any) -> dict[str, Any]:
    if isinstance(duplicate, dict):
        return {
            "group_type": duplicate.get("group_type"),
            "member_paths": sorted(duplicate.get("member_paths", [])),
            "representative_path": duplicate.get("representative_path"),
        }
    return {
        "group_type": getattr(duplicate, "group_type", None),
        "member_paths": sorted(getattr(duplicate, "member_paths", []) or []),
        "representative_path": getattr(duplicate, "representative_path", None),
    }


def _drift_payload(drift: Any) -> dict[str, Any]:
    if isinstance(drift, dict):
        return {
            "drift_type": drift.get("drift_type"),
            "affected_path": drift.get("affected_path"),
            "reference_path": drift.get("reference_path"),
        }
    return {
        "drift_type": getattr(drift, "drift_type", None),
        "affected_path": getattr(drift, "affected_path", None),
        "reference_path": getattr(drift, "reference_path", None),
    }