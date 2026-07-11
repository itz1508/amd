"""
Snapshot scope - bounded capture traversal.
"""
import os
from pathlib import Path
from backend.schemas.snapshot import SnapshotFile, SnapshotNotice
from backend.artifact_store.hashes import compute_sha256


def get_relative_path(file_path: Path, target_root: Path) -> str:
    """Get relative path from target root.
    
    Args:
        file_path: Absolute path to file.
        target_root: Target root directory.
        
    Returns:
        Normalized relative path string.
    """
    try:
        return str(file_path.relative_to(target_root))
    except ValueError:
        return str(file_path)


def process_file(file_path: Path, target_root: Path) -> tuple[SnapshotFile | None, SnapshotNotice | None]:
    """Process a single file and return file record and/or notice.
    
    Args:
        file_path: Absolute path to file.
        target_root: Target root for relative path calculation.
        
    Returns:
        Tuple of (SnapshotFile or None, SnapshotNotice or None).
    """
    relative_path = get_relative_path(file_path, target_root)
    extension = file_path.suffix.lower() if file_path.suffix else ""
    
    # Get file size
    try:
        size_bytes = file_path.stat().st_size
    except OSError as e:
        return None, SnapshotNotice(
            notice_code="unreadable",
            relative_path=relative_path,
            reason=f"Cannot stat file: {e}",
            evidence=str(file_path),
        )
    
    # Try to read file for hashing
    try:
        sha256 = compute_sha256(file_path)
        read_status = "readable"
    except OSError as e:
        return SnapshotFile(
            relative_path=relative_path,
            extension=extension,
            size_bytes=size_bytes,
            sha256="",
            read_status="unreadable",
        ), SnapshotNotice(
            notice_code="unreadable",
            relative_path=relative_path,
            reason=f"Cannot hash file: {e}",
            evidence=str(file_path),
        )
    
    return SnapshotFile(
        relative_path=relative_path,
        extension=extension,
        size_bytes=size_bytes,
        sha256=sha256,
        read_status=read_status,
    ), None