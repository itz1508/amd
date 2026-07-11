"""Automatic cleanup for AMD pipeline artifacts and records."""

import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.run_context import generate_run_id, get_created_at_iso

from .policy import RetentionPolicy, load_policy, DEFAULT_POLICY
from .classifier import (
    ArtifactClassifier,
    ArtifactInfo,
    PERMANENT,
    RETAINED_RUN,
    TEMPORARY,
    EXPIRED,
    PROTECTED_REFERENCE,
    UNKNOWN,
    DELETE,
    PRESERVE,
    SKIP,
)


def get_repo_root() -> Path:
    """Get the repository root path."""
    return Path(os.getcwd()).resolve()


# Default approved cleanup roots (relative to repo root)
DEFAULT_APPROVED_ROOTS = [
    ".runs",
    ".cache",
    "logs",
    "evidence/runs",
]


# Paths that must never be cleaned
PROTECTED_FROM_CLEANUP = [
    ".venv",
    "pyproject.toml",
    "uv.lock",
    "src",
    "tests",
    "fixtures",
    "evidence/finalization",
]


@dataclass
class CleanupPlan:
    """Plan for cleanup operations."""
    run_id: str
    policy_version: str
    mode: str
    approved_roots: list[str]
    files_considered: int = 0
    files_to_delete: list[dict[str, Any]] = field(default_factory=list)
    files_to_preserve: list[dict[str, Any]] = field(default_factory=list)
    files_skipped: list[dict[str, Any]] = field(default_factory=list)
    directories_to_delete: list[dict[str, Any]] = field(default_factory=list)
    directories_to_preserve: list[dict[str, Any]] = field(default_factory=list)
    directories_skipped: list[dict[str, Any]] = field(default_factory=list)
    bytes_to_reclaim: int = 0
    deletion_reasons: dict[str, int] = field(default_factory=dict)
    protection_reasons: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


@dataclass
class CleanupResult:
    """Result of cleanup execution."""
    run_id: str
    policy_version: str
    mode: str
    start_time: str
    end_time: str
    approved_roots: list[str]
    files_considered: int = 0
    files_deleted: list[dict[str, Any]] = field(default_factory=list)
    files_preserved: list[dict[str, Any]] = field(default_factory=list)
    files_skipped: list[dict[str, Any]] = field(default_factory=list)
    directories_deleted: list[dict[str, Any]] = field(default_factory=list)
    directories_preserved: list[dict[str, Any]] = field(default_factory=list)
    directories_skipped: list[dict[str, Any]] = field(default_factory=list)
    bytes_reclaimed: int = 0
    deletion_reasons: dict[str, int] = field(default_factory=dict)
    protection_reasons: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    final_status: str = "completed"


def validate_cleanup_root(root: Path, repo_root: Path) -> tuple[bool, str]:
    """Validate that a cleanup root is safe."""
    try:
        # Resolve the path
        resolved = root.resolve()
        repo_resolved = repo_root.resolve()
        
        # Check if it resolves outside repo
        if not str(resolved).startswith(str(repo_resolved)):
            return False, f"Path {root} resolves outside repository root {repo_root}"
        
        # Check if it's the repo root itself
        if resolved == repo_resolved:
            return False, f"Cannot clean repository root {repo_root}"
        
        # Check if it's a protected path
        for protected in PROTECTED_FROM_CLEANUP:
            protected_path = (repo_resolved / protected).resolve()
            if resolved == protected_path:
                return False, f"Cannot clean protected path {protected}"
        
        # Check for symlinks/junctions escaping repo
        if resolved.is_symlink():
            real_path = resolved.realpath()
            if not str(real_path).startswith(str(repo_resolved)):
                return False, f"Symlink {root} escapes repository"
        
        # Check for path traversal
        if ".." in str(root) or str(root).startswith(".."):
            return False, f"Path traversal detected in {root}"
        
        return True, ""
    
    except Exception as e:
        return False, f"Validation error for {root}: {e}"


def discover_artifacts(root: Path) -> list[Path]:
    """Discover all files and directories in a cleanup root."""
    artifacts = []
    
    if not root.exists():
        return artifacts
    
    # Collect all files and directories
    for item in root.rglob("*"):
        artifacts.append(item)
    
    return artifacts


def build_cleanup_plan(
    approved_roots: list[str | Path],
    repo_root: Path,
    policy: RetentionPolicy,
    dry_run: bool = True,
    apply: bool = False,
) -> CleanupPlan:
    """Build a cleanup plan for approved roots."""
    run_id = generate_run_id()
    plan = CleanupPlan(
        run_id=run_id,
        policy_version=policy.policy_version,
        mode="apply" if apply else "dry_run",
        approved_roots=[str(r) for r in approved_roots],
    )
    
    classifier = ArtifactClassifier(policy)
    
    # Load run artifacts for reference checking
    run_artifacts = load_run_artifacts(repo_root)
    
    for root_str in approved_roots:
        root_path = repo_root / root_str
        
        # Validate root
        is_valid, error = validate_cleanup_root(root_path, repo_root)
        if not is_valid:
            plan.errors.append(f"Skipping invalid root {root_str}: {error}")
            continue
        
        if not root_path.exists():
            continue
        
        # Discover artifacts
        artifacts = discover_artifacts(root_path)
        
        for artifact_path in artifacts:
            plan.files_considered += 1
            
            # Classify artifact
            info = classifier.classify(artifact_path, root_path, run_artifacts)
            
            # Build artifact record
            artifact_record = {
                "path": str(artifact_path),
                "relative_path": str(artifact_path.relative_to(root_path)),
                "is_dir": info.is_dir,
                "size": info.size,
                "classification": info.classification,
                "run_id": info.run_id,
                "run_status": info.run_status,
                "retention_decision": info.retention_decision,
                "reason": info.reason,
                "fingerprint": info.fingerprint,
            }
            
            # Apply retention decision
            if info.retention_decision == DELETE:
                plan.files_to_delete.append(artifact_record)
                plan.bytes_to_reclaim += info.size
                plan.deletion_reasons[info.reason] = plan.deletion_reasons.get(info.reason, 0) + 1
            elif info.retention_decision == PRESERVE:
                plan.files_to_preserve.append(artifact_record)
                plan.protection_reasons[info.reason] = plan.protection_reasons.get(info.reason, 0) + 1
            else:  # SKIP or UNKNOWN
                plan.files_skipped.append(artifact_record)
                plan.protection_reasons[info.reason] = plan.protection_reasons.get(info.reason, 0) + 1
    
    return plan


def load_run_artifacts(repo_root: Path) -> dict[str, Any]:
    """Load run artifacts metadata for reference checking."""
    # Try to load from latest.json or similar
    latest_path = repo_root / "latest.json"
    if latest_path.exists():
        try:
            with open(latest_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    
    # Try evidence/runs
    evidence_runs = repo_root / "evidence" / "runs"
    if evidence_runs.exists():
        runs = {}
        for run_dir in evidence_runs.iterdir():
            if run_dir.is_dir():
                run_id = run_dir.name
                runs[run_id] = {"run_id": run_id, "status": "unknown"}
                # Try to get status
                for artifact in run_dir.glob("*.json"):
                    try:
                        with open(artifact, 'r') as f:
                            data = json.load(f)
                            if "status" in data:
                                runs[run_id]["status"] = data["status"]
                            if "timestamp" in data or "created_at" in data:
                                runs[run_id]["timestamp"] = data.get("timestamp", data.get("created_at", ""))
                    except (json.JSONDecodeError, OSError):
                        pass
        return {"runs": runs}
    
    return {"runs": {}}


def execute_cleanup(plan: CleanupPlan, repo_root: Path) -> CleanupResult:
    """Execute the cleanup plan."""
    start_time = get_created_at_iso()
    
    result = CleanupResult(
        run_id=plan.run_id,
        policy_version=plan.policy_version,
        mode=plan.mode,
        start_time=start_time,
        end_time="",
        approved_roots=plan.approved_roots,
        files_considered=plan.files_considered,
        bytes_reclaimed=0,
        deletion_reasons=plan.deletion_reasons.copy(),
        protection_reasons=plan.protection_reasons.copy(),
        errors=plan.errors.copy(),
    )
    
    # Only perform deletions in apply mode
    if plan.mode == "apply":
        for artifact_record in plan.files_to_delete:
            path = Path(artifact_record["path"])
            
            # Re-validate before deletion
            if not path.exists():
                result.files_skipped.append(artifact_record)
                result.files_skipped[-1]["skip_reason"] = "File no longer exists"
                continue
            
            # Check fingerprint didn't change
            classifier = ArtifactClassifier()
            current_info = classifier._gather_info(path)
            if current_info.fingerprint != artifact_record.get("fingerprint", ""):
                result.files_skipped.append(artifact_record)
                result.files_skipped[-1]["skip_reason"] = "Fingerprint changed"
                result.errors.append(f"Fingerprint mismatch for {path}, skipping deletion")
                continue
            
            # Perform deletion
            try:
                if path.is_file():
                    path.unlink()
                    result.bytes_reclaimed += artifact_record["size"]
                    result.files_deleted.append(artifact_record)
                elif path.is_dir():
                    # Remove directory and all contents
                    import shutil
                    size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
                    shutil.rmtree(path)
                    result.bytes_reclaimed += size
                    result.directories_deleted.append(artifact_record)
            except (OSError, PermissionError) as e:
                result.errors.append(f"Failed to delete {path}: {e}")
                result.files_skipped.append(artifact_record)
                result.files_skipped[-1]["skip_reason"] = f"Deletion error: {e}"
    
    result.end_time = get_created_at_iso()
    
    if result.errors:
        result.final_status = "error"
    elif result.files_deleted or result.directories_deleted:
        result.final_status = "completed_with_deletions"
    else:
        result.final_status = "completed_no_deletions"
    
    return result


def write_cleanup_evidence(
    output_dir: Path,
    plan: CleanupPlan,
    result: CleanupResult | None = None,
) -> int:
    """Write cleanup evidence files."""
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Write cleanup plan
        plan_dict = {
            "cleanup_run_id": plan.run_id,
            "policy_version": plan.policy_version,
            "mode": plan.mode,
            "approved_roots": plan.approved_roots,
            "files_considered": plan.files_considered,
            "files_to_delete": plan.files_to_delete,
            "files_to_preserve": plan.files_to_preserve,
            "files_skipped": plan.files_skipped,
            "directories_to_delete": plan.directories_to_delete,
            "directories_to_preserve": plan.directories_to_preserve,
            "directories_skipped": plan.directories_skipped,
            "bytes_to_reclaim": plan.bytes_to_reclaim,
            "deletion_reasons": plan.deletion_reasons,
            "protection_reasons": plan.protection_reasons,
            "errors": plan.errors,
            "created_at": get_created_at_iso(),
        }
        
        with open(output_dir / "cleanup_plan.json", 'w') as f:
            json.dump(plan_dict, f, indent=2, default=str)
        
        # Write cleanup result if provided
        if result:
            result_dict = {
                "cleanup_run_id": result.run_id,
                "policy_version": result.policy_version,
                "mode": result.mode,
                "start_time": result.start_time,
                "end_time": result.end_time,
                "approved_roots": result.approved_roots,
                "files_considered": result.files_considered,
                "files_deleted": result.files_deleted,
                "files_preserved": result.files_preserved,
                "files_skipped": result.files_skipped,
                "directories_deleted": result.directories_deleted,
                "directories_preserved": result.directories_preserved,
                "directories_skipped": result.directories_skipped,
                "bytes_reclaimed": result.bytes_reclaimed,
                "deletion_reasons": result.deletion_reasons,
                "protection_reasons": result.protection_reasons,
                "errors": result.errors,
                "final_status": result.final_status,
                "created_at": get_created_at_iso(),
            }
            
            with open(output_dir / "cleanup_result.json", 'w') as f:
                json.dump(result_dict, f, indent=2, default=str)
            
            # Write deletion manifest
            deletion_manifest = {
                "cleanup_run_id": result.run_id,
                "policy_version": result.policy_version,
                "mode": result.mode,
                "approved_roots": result.approved_roots,
                "files_deleted": [
                    {
                        "path": d["path"],
                        "classification": d.get("classification", "unknown"),
                        "size": d.get("size", 0),
                        "fingerprint": d.get("fingerprint", ""),
                        "reason": d.get("reason", ""),
                        "associated_run_id": d.get("run_id"),
                        "deletion_timestamp": get_created_at_iso(),
                    }
                    for d in result.files_deleted
                ],
                "directories_deleted": [
                    {
                        "path": d["path"],
                        "classification": d.get("classification", "unknown"),
                        "size": d.get("size", 0),
                        "fingerprint": d.get("fingerprint", ""),
                        "reason": d.get("reason", ""),
                        "associated_run_id": d.get("run_id"),
                        "deletion_timestamp": get_created_at_iso(),
                    }
                    for d in result.directories_deleted
                ],
                "files_preserved": result.files_preserved,
                "files_skipped": result.files_skipped,
                "bytes_reclaimed": result.bytes_reclaimed,
                "deletion_reasons": result.deletion_reasons,
                "protection_reasons": result.protection_reasons,
                "errors": result.errors,
                "final_status": result.final_status,
                "created_at": get_created_at_iso(),
            }
            
            with open(output_dir / "deletion_manifest.json", 'w') as f:
                json.dump(deletion_manifest, f, indent=2, default=str)
        
        return 0
    
    except Exception as e:
        print(f"Error writing cleanup evidence: {e}", file=sys.stderr)
        return 1


def write_cleanup_markdown(
    output_dir: Path,
    plan: CleanupPlan,
    result: CleanupResult | None = None,
) -> int:
    """Write human-readable cleanup report."""
    try:
        lines = []
        lines.append("# Cleanup Report")
        lines.append("")
        lines.append(f"**Run ID:** {plan.run_id}")
        lines.append(f"**Policy Version:** {plan.policy_version}")
        lines.append(f"**Mode:** {plan.mode}")
        lines.append(f"**Timestamp:** {get_created_at_iso()}")
        lines.append("")
        
        lines.append("## Approved Roots")
        for root in plan.approved_roots:
            lines.append(f"- `{root}`")
        lines.append("")
        
        lines.append("## Summary")
        lines.append(f"- Files considered: {plan.files_considered}")
        lines.append(f"- Files to delete: {len(plan.files_to_delete)}")
        lines.append(f"- Files to preserve: {len(plan.files_to_preserve)}")
        lines.append(f"- Files skipped: {len(plan.files_skipped)}")
        lines.append(f"- Bytes to reclaim: {plan.bytes_to_reclaim}")
        lines.append("")
        
        if result:
            lines.append("## Results")
            lines.append(f"- Files deleted: {len(result.files_deleted)}")
            lines.append(f"- Directories deleted: {len(result.directories_deleted)}")
            lines.append(f"- Bytes reclaimed: {result.bytes_reclaimed}")
            lines.append(f"- Final status: {result.final_status}")
            lines.append("")
        
        if plan.errors:
            lines.append("## Errors")
            for error in plan.errors:
                lines.append(f"- {error}")
            lines.append("")
        
        if plan.deletion_reasons:
            lines.append("## Deletion Reasons")
            for reason, count in plan.deletion_reasons.items():
                lines.append(f"- {reason}: {count}")
            lines.append("")
        
        if plan.protection_reasons:
            lines.append("## Protection Reasons")
            for reason, count in plan.protection_reasons.items():
                lines.append(f"- {reason}: {count}")
            lines.append("")
        
        with open(output_dir / "cleanup_result.md", 'w') as f:
            f.write("\n".join(lines))
        
        return 0
    
    except Exception as e:
        print(f"Error writing cleanup markdown: {e}", file=sys.stderr)
        return 1


def run_cleanup(
    approved_roots: list[str] | None = None,
    policy_path: str | None = None,
    dry_run: bool = True,
    apply: bool = False,
    output_dir: str | Path | None = None,
) -> int:
    """Run artifact cleanup.
    
    Args:
        approved_roots: List of approved cleanup roots (relative to repo root or absolute)
        policy_path: Path to custom retention policy JSON file
        dry_run: If True, only plan without deleting (default: True)
        apply: If True, perform deletions (requires explicit --apply flag)
        output_dir: Directory to write evidence files
        
    Returns:
        Exit code (0 for success, 1 for error)
    """
    import os
    
    repo_root = get_repo_root()
    
    # Load policy
    policy = load_policy(policy_path)
    
    # Use default approved roots if not specified
    cleanup_roots = approved_roots or DEFAULT_APPROVED_ROOTS
    
    # Convert relative paths to absolute (relative to repo root)
    resolved_roots = []
    for root in cleanup_roots:
        root_path = Path(root)
        if root_path.is_absolute():
            resolved_roots.append(str(root_path))
        else:
            # Relative to repo root
            resolved_roots.append(str(repo_root / root_path))
    
    # Build cleanup plan
    plan = build_cleanup_plan(
        approved_roots=resolved_roots,
        repo_root=repo_root,
        policy=policy,
        dry_run=dry_run,
        apply=apply,
    )
    
    # Determine output directory
    if output_dir:
        out_dir = Path(output_dir)
    else:
        out_dir = repo_root / ".runs" / plan.run_id
    
    # Execute cleanup if in apply mode
    result = None
    if apply:
        result = execute_cleanup(plan, repo_root)
    
    # Write evidence
    write_cleanup_evidence(out_dir, plan, result)
    write_cleanup_markdown(out_dir, plan, result)
    
    # Also write cleanup_result.json for dry-run mode
    if not apply and result is None:
        # Create a result-like dict for dry-run
        result_dict = {
            "cleanup_run_id": plan.run_id,
            "policy_version": plan.policy_version,
            "mode": plan.mode,
            "start_time": get_created_at_iso(),
            "end_time": get_created_at_iso(),
            "approved_roots": plan.approved_roots,
            "files_considered": plan.files_considered,
            "files_deleted": plan.files_to_delete,
            "files_preserved": plan.files_to_preserve,
            "files_skipped": plan.files_skipped,
            "directories_deleted": plan.directories_to_delete,
            "directories_preserved": plan.directories_to_preserve,
            "directories_skipped": plan.directories_skipped,
            "bytes_reclaimed": 0,
            "deletion_reasons": plan.deletion_reasons,
            "protection_reasons": plan.protection_reasons,
            "errors": plan.errors,
            "final_status": "completed",
        }
        
        result_file = out_dir / "cleanup_result.json"
        result_file.parent.mkdir(parents=True, exist_ok=True)
        with open(result_file, 'w') as f:
            json.dump(result_dict, f, indent=2, default=str)
    
    # Print summary
    print(f"Cleanup {plan.mode} completed: {plan.run_id}")
    print(f"  Files considered: {plan.files_considered}")
    print(f"  Files to delete: {len(plan.files_to_delete)}")
    print(f"  Files to preserve: {len(plan.files_to_preserve)}")
    print(f"  Files skipped: {len(plan.files_skipped)}")
    print(f"  Bytes to reclaim: {plan.bytes_to_reclaim}")
    
    if result:
        print(f"  Files deleted: {len(result.files_deleted)}")
        print(f"  Directories deleted: {len(result.directories_deleted)}")
        print(f"  Bytes reclaimed: {result.bytes_reclaimed}")
        print(f"  Final status: {result.final_status}")
    
    if plan.errors:
        print(f"  Errors: {len(plan.errors)}")
        for error in plan.errors:
            print(f"    - {error}")
    
    if apply and result and result.errors:
        return 1
    
    return 0


def main(args: list[str] | None = None) -> int:
    """CLI entry point for cleanup command."""
    import argparse
    
    parser = argparse.ArgumentParser(
        prog="cleanup",
        description="AMD pipeline artifact cleanup"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Perform actual deletions (default is dry-run)"
    )
    parser.add_argument(
        "--policy",
        type=str,
        default=None,
        help="Path to custom retention policy JSON file"
    )
    parser.add_argument(
        "--roots",
        type=str,
        nargs="*",
        default=None,
        help="Approved cleanup roots (space-separated, relative to repo root)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory to write evidence files"
    )
    
    parsed = parser.parse_args(args)
    
    return run_cleanup(
        approved_roots=parsed.roots,
        policy_path=parsed.policy,
        dry_run=not parsed.apply,
        apply=parsed.apply,
        output_dir=parsed.output_dir,
    )
