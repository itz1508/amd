"""
Snapshot runner - main entry point.
"""
import hashlib
import json
import os
import sys
from pathlib import Path
from backend.schemas.snapshot import Snapshot_Output, SnapshotFile, SnapshotNotice
from backend.paths import resolve_target, resolve_output_root, OutputBoundaryError
from backend.artifact_store.writer import write_json_artifact, ArtifactWriteError
from backend.phases.snapshot.evidence_scope import evaluate_evidence_path
from backend.phases.snapshot.scope import process_file, get_relative_path


def compute_snapshot_fingerprint(
    files: list[SnapshotFile],
    notices: list[SnapshotNotice],
) -> str:
    """Compute deterministic fingerprint from stable content only.
    
    Includes only: relative_path, size_bytes, sha256 (files), 
    and notice_code, relative_path, reason (notices).
    Excludes: target_root, timestamps, artifact paths.
    
    Args:
        files: List of sorted SnapshotFile records.
        notices: List of sorted SnapshotNotice records.
        
    Returns:
        SHA-256 fingerprint hex string.
    """
    payload = {
        "files": [
            {
                "relative_path": f.relative_path,
                "size_bytes": f.size_bytes,
                "sha256": f.sha256,
            }
            for f in files
        ],
        "notices": [
            {
                "notice_code": n.notice_code,
                "relative_path": n.relative_path,
                "reason": n.reason,
            }
            for n in notices
        ],
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def walk_target_with_notices(target_root: Path) -> tuple[list[Path], list[SnapshotNotice]]:
    """Walk target directory with exclusion notices.
    
    Produces a prunable walk: skips excluded directories without traversing them,
    and emits notices for excluded paths encountered.
    
    Args:
        target_root: Resolved target directory.
        
    Returns:
        Tuple of (files_to_process, exclusion_notices).
    """
    files: list[Path] = []
    notices: list[SnapshotNotice] = []
    
    # Use os.walk for prunable traversal
    for root, dirs, filenames in os.walk(target_root):
        root_path = Path(root)
        
        # Check for excluded directories at this level
        excluded_dirs = []
        for dirname in list(dirs):  # copy since we modify in place
            dir_path = root_path / dirname
            decision = evaluate_evidence_path(dir_path, is_dir=True)
            if not decision.included:
                excluded_dirs.append(dirname)
                notices.append(SnapshotNotice(
                    notice_code="excluded",
                    relative_path=get_relative_path(dir_path, target_root),
                    reason=decision.reason,
                    evidence=str(dir_path),
                ))
        
        # Prune excluded directories from traversal
        for dirname in excluded_dirs:
            dirs.remove(dirname)
        
        # Process files in this directory
        for filename in filenames:
            file_path = root_path / filename
            decision = evaluate_evidence_path(file_path, is_dir=False)
            if decision.included:
                files.append(file_path)
            else:
                notices.append(SnapshotNotice(
                    notice_code="excluded",
                    relative_path=get_relative_path(file_path, target_root),
                    reason=decision.reason,
                    evidence=str(file_path),
                ))
    
    return files, notices


def run_snapshot(target: str | Path, output_root: str | Path) -> Snapshot_Output:
    """Run snapshot phase on target.
    
    Args:
        target: Target directory path.
        output_root: Output directory path (must be outside target).
        
    Returns:
        Snapshot_Output with captured state.
        
    Raises:
        ValueError: If target is missing or not a directory.
        OutputBoundaryError: If output_root is inside target.
    """
    # Resolve target
    target_path = resolve_target(target)
    
    # Resolve and validate output root
    output_path = resolve_output_root(output_root, target_path)
    
    # Walk files with exclusion notices
    files_to_process, exclusion_notices = walk_target_with_notices(target_path)
    
    # Process files
    captured_files: list[SnapshotFile] = []
    file_notices: list[SnapshotNotice] = list(exclusion_notices)
    
    for file_path in files_to_process:
        file_record, notice = process_file(file_path, target_path)
        if file_record:
            captured_files.append(file_record)
        if notice:
            file_notices.append(notice)
    
    # Sort for deterministic output
    captured_files.sort(key=lambda f: f.relative_path)
    file_notices.sort(key=lambda n: (n.notice_code, n.relative_path))
    
    # Compute fingerprint
    fingerprint = compute_snapshot_fingerprint(captured_files, file_notices)
    
    # Determine status
    status = "completed" if not file_notices else "completed_with_notices"
    
    # Write artifact
    artifact_path = output_path / "01_snapshot.json"
    try:
        write_json_artifact(
            artifact_path,
            Snapshot_Output(
                phase="snapshot",
                target_root=str(target_path),
                status=status,
                files=captured_files,
                notices=file_notices,
                snapshot_fingerprint=fingerprint,
            ).to_dict()
        )
    except ArtifactWriteError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        raise
    
    return Snapshot_Output(
        phase="snapshot",
        target_root=str(target_path),
        status=status,
        files=captured_files,
        notices=file_notices,
        snapshot_fingerprint=fingerprint,
    )


def main(args: list[str] | None = None) -> int:
    """CLI entry point for snapshot phase.
    
    Args:
        args: Command line arguments (defaults to sys.argv).
        
    Returns:
        Exit code (0 for success, 1 for error).
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        prog="snapshot",
        description="Snapshot phase - capture filesystem state"
    )
    parser.add_argument(
        "target",
        help="Target directory to snapshot"
    )
    parser.add_argument(
        "--output-root",
        required=True,
        help="Output directory for artifacts (required, must be outside target)"
    )
    
    parsed = parser.parse_args(args)
    
    try:
        result = run_snapshot(parsed.target, parsed.output_root)
        print(f"Snapshot completed: {parsed.target}")
        print(f"  Files captured: {len(result.files)}")
        print(f"  Notices: {len(result.notices)}")
        print(f"  Output: {Path(parsed.output_root) / '01_snapshot.json'}")
        return 0
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except OutputBoundaryError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except ArtifactWriteError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
