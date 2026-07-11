"""Final_Result locking functionality."""
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any
from .schema import Final_Result_Input, Final_Result_Lock
from .errors import AlreadyLockedError, IdempotentMismatchError


# Lock storage directory
_lock_storage_dir = Path(tempfile.gettempdir()) / "final_result_locks"
_lock_storage_dir.mkdir(parents=True, exist_ok=True)


def _lock_file_path(final_result_id: str) -> Path:
    """Get path to lock file for a final result."""
    return _lock_storage_dir / f"{final_result_id}.lock"


def compute_lock_fingerprint(
    source_phase: str,
    source_status: str,
    source_fingerprint: str,
    terminal_state: str,
    route_history: list[dict[str, Any]],
    dossier_evidence_refs: list[str],
    failure_reasons: list[str],
    result_summary: str,
    cleanup_requested: bool,
) -> str:
    """Compute deterministic lock fingerprint."""
    payload = {
        "source_phase": source_phase,
        "source_status": source_status,
        "source_fingerprint": source_fingerprint,
        "terminal_state": terminal_state,
        "route_history": sorted(route_history, key=lambda x: str(x) if isinstance(x, dict) else str(x)),
        "dossier_evidence_refs": sorted(dossier_evidence_refs),
        "failure_reasons": sorted(failure_reasons),
        "result_summary": result_summary,
        "cleanup_requested": cleanup_requested,
    }
    
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def compute_final_result_id(
    source_phase: str,
    source_fingerprint: str,
    terminal_state: str,
) -> str:
    """Compute deterministic final_result_id."""
    payload = {
        "source_phase": source_phase,
        "source_fingerprint": source_fingerprint,
        "terminal_state": terminal_state,
    }
    
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def create_lock(input_data: Final_Result_Input) -> Final_Result_Lock:
    """Create a lock for Final_Result."""
    final_result_id = compute_final_result_id(
        input_data.source_phase,
        input_data.source_fingerprint,
        input_data.terminal_state,
    )
    
    lock_fingerprint = compute_lock_fingerprint(
        input_data.source_phase,
        input_data.source_status,
        input_data.source_fingerprint,
        input_data.terminal_state,
        input_data.route_history,
        input_data.dossier_evidence_refs,
        input_data.failure_reasons,
        input_data.result_summary,
        input_data.cleanup_requested,
    )
    
    return Final_Result_Lock(
        final_result_id=final_result_id,
        lock_fingerprint=lock_fingerprint,
        locked=False,
    )


def _read_lock_file(lock_path: Path) -> Final_Result_Lock | None:
    """Read lock from file."""
    if not lock_path.exists():
        return None
    
    try:
        with open(lock_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Final_Result_Lock(
            final_result_id=data["final_result_id"],
            lock_fingerprint=data["lock_fingerprint"],
            locked=data.get("locked", False),
            locked_at=data.get("locked_at", ""),
        )
    except (json.JSONDecodeError, OSError, KeyError):
        return None


def check_lock(final_result_id: str, lock_fingerprint: str) -> bool:
    """Check if a lock exists and is valid.
    
    Returns True if already locked with same fingerprint (idempotent request).
    Returns False if not locked or different fingerprint.
    """
    lock_path = _lock_file_path(final_result_id)
    existing_lock = _read_lock_file(lock_path)
    
    if existing_lock is None:
        return False
    
    if existing_lock.locked and existing_lock.lock_fingerprint == lock_fingerprint:
        return True
    
    return False


def _write_lock_file(lock: Final_Result_Lock) -> None:
    """Write lock to file."""
    lock_path = _lock_file_path(lock.final_result_id)
    import datetime
    if not lock.locked_at:
        lock.locked_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    lock_data = {
        "final_result_id": lock.final_result_id,
        "lock_fingerprint": lock.lock_fingerprint,
        "locked": lock.locked,
        "locked_at": lock.locked_at,
    }
    
    # Atomic write
    temp_path = lock_path.with_suffix(".tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(lock_data, f)
    temp_path.replace(lock_path)


def acquire_lock(lock: Final_Result_Lock) -> None:
    """Acquire a lock. Raises if already locked with different content."""
    lock_path = _lock_file_path(lock.final_result_id)
    existing_lock = _read_lock_file(lock_path)
    
    if existing_lock is not None:
        if existing_lock.locked:
            if existing_lock.lock_fingerprint != lock.lock_fingerprint:
                raise IdempotentMismatchError(
                    f"Final result {lock.final_result_id} already locked with different content"
                )
            # Same fingerprint - idempotent request, allow
            return
        else:
            # Already exists but not locked - this shouldn't happen
            raise AlreadyLockedError(
                f"Final result {lock.final_result_id} already exists but not locked"
            )
    
    # Store the lock
    import datetime
    lock.locked = True
    lock.locked_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    _write_lock_file(lock)


def is_locked(final_result_id: str) -> bool:
    """Check if a final result is locked."""
    lock_path = _lock_file_path(final_result_id)
    existing_lock = _read_lock_file(lock_path)
    return existing_lock is not None and existing_lock.locked


def get_lock(final_result_id: str) -> Final_Result_Lock | None:
    """Get lock for a final result."""
    lock_path = _lock_file_path(final_result_id)
    return _read_lock_file(lock_path)


def clear_locks() -> None:
    """Clear all locks (for testing purposes)."""
    import shutil
    for lock_file in _lock_storage_dir.glob("*.lock"):
        try:
            lock_file.unlink()
        except OSError:
            pass


def final_result_fingerprint(
    source_phase: str,
    source_status: str,
    source_fingerprint: str,
    terminal_state: str,
    route_history: list[dict[str, Any]],
    dossier_evidence_refs: list[str],
    failure_reasons: list[str],
    result_summary: str,
    cleanup_requested: bool,
    next_route: str | None,
) -> str:
    """Compute deterministic final_result_fingerprint.
    
    Must include:
    - source phase
    - source status
    - source fingerprint
    - terminal state
    - ordered route history
    - ordered evidence references
    - ordered failure reasons
    - result summary
    - cleanup request
    - final route
    
    Exclude:
    - timestamps
    - run identifiers
    - temporary paths
    - output_root
    - artifact location
    - machine-specific absolute paths
    """
    payload = {
        "source_phase": source_phase,
        "source_status": source_status,
        "source_fingerprint": source_fingerprint,
        "terminal_state": terminal_state,
        "route_history": sorted(route_history, key=lambda x: str(x) if isinstance(x, dict) else str(x)),
        "dossier_evidence_refs": sorted(dossier_evidence_refs),
        "failure_reasons": sorted(failure_reasons),
        "result_summary": result_summary,
        "cleanup_requested": cleanup_requested,
        "next_route": next_route,
    }
    
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()