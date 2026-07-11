"""
Deterministic fingerprint helpers for Inspection.
"""
import hashlib
import json
from typing import Any


def _canonicalize(value: Any) -> Any:
    """Recursively canonicalize a value for stable hashing.

    Mappings are sorted by key. Sequences are preserved but their items are
    canonicalized. Strings, numbers, booleans, and None pass through.
    """
    if isinstance(value, dict):
        return {k: _canonicalize(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        return [_canonicalize(v) for v in value]
    if isinstance(value, tuple):
        return tuple(_canonicalize(v) for v in value)
    if isinstance(value, set):
        raise ValueError("Sets are not deterministic; convert to a sorted list.")
    return value


def compute_fingerprint(payload: dict[str, Any]) -> str:
    """Compute a deterministic SHA-256 fingerprint from a canonical payload.

    The payload is canonicalized (sorted mappings, stable sequences) and then
    serialized with sorted keys and no whitespace. Timestamps, random UUIDs,
    temporary paths, process IDs, and memory addresses must not be included by
    callers.
    """
    canonical = _canonicalize(payload)
    serialized = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def compute_inspection_id(input_payload: dict[str, Any]) -> str:
    """Compute a deterministic inspection identifier from canonical input.

    The identifier is derived from the stable fields of the input so that
    identical canonical input always yields the same inspection_id.
    """
    canonical = _canonicalize(input_payload)
    serialized = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()