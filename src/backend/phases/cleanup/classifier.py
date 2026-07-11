"""Artifact classification for AMD pipeline cleanup."""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .policy import RetentionPolicy, DEFAULT_POLICY


@dataclass
class ArtifactInfo:
    """Information about a discovered artifact."""
    path: Path
    is_dir: bool
    size: int
    created_time: datetime | None
    modified_time: datetime | None
    classification: str
    run_id: str | None = None
    run_status: str | None = None
    reference_status: str | None = None
    retention_decision: str = ""
    reason: str = ""
    fingerprint: str = ""


PERMANENT = "permanent"
RETAINED_RUN = "retained_run"
TEMPORARY = "temporary"
EXPIRED = "expired"
PROTECTED_REFERENCE = "protected_reference"
UNKNOWN = "unknown"

DELETE = "delete"
PRESERVE = "preserve"
SKIP = "skip"


PROTECTED_PATHS = {
    ".venv",
    "pyproject.toml",
    "uv.lock",
    "src",
    "tests",
    "fixtures",
    "evidence/finalization",
}


TEMPORARY_PATTERNS = {
    ".tmp",
    "~",
    ".bak",
    ".swp",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".DS_Store",
    "Thumbs.db",
    "*.temp",
    "*.tmpproj",
    ".atomic-write",
}


RUN_ARTIFACT_PATTERNS = {
    "01_snapshot.json",
    "02_scan.json",
    "03_analysis_classification.json",
    "04_statement_output.json",
    "05_gap_evaluation.json",
    "06_simulation_environment.json",
    "07_inspection.json",
    "08_final_result.json",
    "09_cleanup.json",
    "latest.json",
    "cleanup_report.json",
    "cleanup_validation.json",
    "run_manifest.json",
    "artifact_index.json",
}


class ArtifactClassifier:
    """Classifies artifacts for cleanup decisions."""
    
    def __init__(self, policy: RetentionPolicy | None = None):
        """Initialize classifier with retention policy."""
        self.policy = policy or RetentionPolicy(DEFAULT_POLICY)
    
    def classify(self, path: Path, root: Path, run_artifacts: dict[str, Any] | None = None) -> ArtifactInfo:
        """Classify an artifact and determine retention decision."""
        info = self._gather_info(path)
        
        if self._is_protected(path, root):
            info.classification = PERMANENT
            info.retention_decision = PRESERVE
            info.reason = "Path is in protected paths list"
            return info
        
        if info.is_dir and self._is_run_directory(path):
            run_id = path.name
            status = self._get_run_status(path)
            info.run_id = run_id
            info.run_status = status
            
            if status == "success":
                info.classification = RETAINED_RUN
                info.retention_decision = self._decide_run_retention(path, root, status, run_artifacts)
            elif status == "failed":
                info.classification = RETAINED_RUN
                info.retention_decision = self._decide_run_retention(path, root, status, run_artifacts)
            else:
                info.classification = UNKNOWN
                info.retention_decision = SKIP
                info.reason = "Run status unknown"
            return info
        
        if path.name in RUN_ARTIFACT_PATTERNS:
            info.classification = RETAINED_RUN
            info.retention_decision = PRESERVE
            info.reason = "Run artifact file"
            return info
        
        if self._is_temporary(path):
            info.classification = TEMPORARY
            info.retention_decision = DELETE
            info.reason = "Temporary file - eligible for deletion"
            return info
        
        if "evidence/finalization" in str(path):
            info.classification = PERMANENT
            info.retention_decision = PRESERVE
            info.reason = "Finalization evidence"
            return info
        
        if run_artifacts and self._is_referenced(path, run_artifacts):
            info.classification = PROTECTED_REFERENCE
            info.retention_decision = PRESERVE
            info.reason = "Referenced by active run"
            return info
        
        info.classification = UNKNOWN
        info.retention_decision = SKIP
        info.reason = "Unknown classification"
        return info
    
    def _gather_info(self, path: Path) -> ArtifactInfo:
        """Gather basic information about a path."""
        try:
            is_dir = path.is_dir()
            size = self._get_size(path) if path.exists() else 0
            created_time = self._get_timestamp(path, "created")
            modified_time = self._get_timestamp(path, "modified")
            fingerprint = self._compute_fingerprint(path) if path.exists() else ""
            
            return ArtifactInfo(
                path=path,
                is_dir=is_dir,
                size=size,
                created_time=created_time,
                modified_time=modified_time,
                classification=UNKNOWN,
                fingerprint=fingerprint,
            )
        except Exception:
            return ArtifactInfo(
                path=path,
                is_dir=False,
                size=0,
                created_time=None,
                modified_time=None,
                classification=UNKNOWN,
                fingerprint="",
            )
    
    def _get_size(self, path: Path) -> int:
        """Get total size of path (file or directory)."""
        if path.is_file():
            return path.stat().st_size
        elif path.is_dir():
            total = 0
            for f in path.rglob("*"):
                if f.is_file():
                    total += f.stat().st_size
            return total
        return 0
    
    def _get_timestamp(self, path: Path, which: str) -> datetime | None:
        """Get creation or modification timestamp."""
        try:
            stat = path.stat()
            if which == "created":
                return datetime.fromtimestamp(stat.st_ctime)
            else:
                return datetime.fromtimestamp(stat.st_mtime)
        except (OSError, ValueError):
            return None
    
    def _compute_fingerprint(self, path: Path) -> str:
        """Compute a simple fingerprint for the path."""
        import hashlib
        
        if path.is_file():
            try:
                with open(path, 'rb') as f:
                    content = f.read(8192)
                return hashlib.md5(content).hexdigest()[:16]
            except (OSError, IOError):
                return "unreadable"
        elif path.is_dir():
            files = sorted([f.name for f in path.iterdir() if f.is_file()])
            return hashlib.md5(",".join(files).encode()).hexdigest()[:16]
        return "unknown"
    
    def _is_protected(self, path: Path, root: Path) -> bool:
        """Check if path is in protected paths."""
        try:
            relative_path = path.relative_to(root)
        except ValueError:
            return False
        
        path_parts = str(relative_path).replace("\\", "/").split("/")
        
        for protected in PROTECTED_PATHS:
            protected_parts = protected.replace("\\", "/").split("/")
            for i in range(len(path_parts)):
                if "/".join(path_parts[:i+1]) == protected:
                    return True
                if path_parts[i] == protected:
                    return True
        
        return False
    
    def _is_run_directory(self, path: Path) -> bool:
        """Check if path is a run directory (contains run artifacts)."""
        if not path.is_dir():
            return False
        for pattern in RUN_ARTIFACT_PATTERNS:
            if (path / pattern).exists():
                return True
        return False
    
    def _get_run_status(self, path: Path) -> str | None:
        """Get run status from run directory."""
        final_result_path = path / "08_final_result.json"
        if final_result_path.exists():
            try:
                with open(final_result_path, 'r') as f:
                    data = json.load(f)
                    return data.get("status", "unknown")
            except (json.JSONDecodeError, OSError):
                pass
        cleanup_path = path / "09_cleanup.json"
        if cleanup_path.exists():
            try:
                with open(cleanup_path, 'r') as f:
                    data = json.load(f)
                    return data.get("cleanup_status", "unknown")
            except (json.JSONDecodeError, OSError):
                pass
        return None
    
    def _decide_run_retention(self, path: Path, root: Path, status: str, run_artifacts: dict[str, Any] | None) -> str:
        """Decide retention for a run directory."""
        modified_time = self._get_timestamp(path, "modified")
        
        if not modified_time:
            return SKIP
        
        max_age = timedelta(days=self.policy.max_age_days)
        if datetime.now() - modified_time > max_age:
            if status == "failed":
                return PRESERVE
            return DELETE
        
        if run_artifacts:
            if status == "success":
                successful_runs = [
                    r for r in run_artifacts.get("runs", [])
                    if r.get("status") == "success"
                ]
                successful_runs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
                if path.name in [r.get("run_id") for r in successful_runs[:self.policy.keep_latest_successful]]:
                    return PRESERVE
                return DELETE
            elif status == "failed":
                failed_runs = [
                    r for r in run_artifacts.get("runs", [])
                    if r.get("status") == "failed"
                ]
                failed_runs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
                if path.name in [r.get("run_id") for r in failed_runs[:self.policy.keep_latest_failed]]:
                    return PRESERVE
                return DELETE
        
        return PRESERVE
    
    def _is_temporary(self, path: Path) -> bool:
        """Check if path matches temporary patterns."""
        path_str = str(path.name).lower()
        for pattern in TEMPORARY_PATTERNS:
            if pattern.startswith("*") and pattern.endswith("*"):
                if pattern[1:-1] in path_str:
                    return True
            elif pattern.startswith("*"):
                if path_str.endswith(pattern[1:]):
                    return True
            elif pattern.endswith("*"):
                if path_str.startswith(pattern[:-1]):
                    return True
            else:
                if path_str == pattern.lower():
                    return True
        return False
    
    def _is_referenced(self, path: Path, run_artifacts: dict[str, Any]) -> bool:
        """Check if artifact is referenced by active runs."""
        path_str = str(path)
        for run_id, run_data in run_artifacts.get("runs", {}).items():
            if run_data.get("active", False):
                if path_str in str(run_data):
                    return True
        return False
