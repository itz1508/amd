"""Retention policy for AMD pipeline artifact cleanup."""

from typing import Any

# Default retention policy
DEFAULT_POLICY = {
    "policy_version": "1.0",
    "keep_latest_successful": 3,
    "keep_latest_failed": 3,
    "max_age_days": 14,
    "delete_temporary_on_success": True,
    "delete_temporary_on_failure": False,
    "preserve_finalization_evidence": True,
    "preserve_active_references": True,
    "dry_run_default": True,
}


class RetentionPolicy:
    """Immutable retention policy configuration."""
    
    def __init__(self, policy_dict: dict[str, Any] | None = None):
        """Initialize retention policy from dict or use defaults."""
        self._policy = policy_dict or DEFAULT_POLICY.copy()
        self._validate()
    
    def _validate(self) -> None:
        """Validate policy values."""
        if self.keep_latest_successful < 0:
            raise ValueError("keep_latest_successful must be non-negative")
        if self.keep_latest_failed < 0:
            raise ValueError("keep_latest_failed must be non-negative")
        if self.max_age_days < 0:
            raise ValueError("max_age_days must be non-negative")
    
    @property
    def policy_version(self) -> str:
        return str(self._policy.get("policy_version", "1.0"))
    
    @property
    def keep_latest_successful(self) -> int:
        return int(self._policy.get("keep_latest_successful", 3))
    
    @property
    def keep_latest_failed(self) -> int:
        return int(self._policy.get("keep_latest_failed", 3))
    
    @property
    def max_age_days(self) -> int:
        return int(self._policy.get("max_age_days", 14))
    
    @property
    def delete_temporary_on_success(self) -> bool:
        return bool(self._policy.get("delete_temporary_on_success", True))
    
    @property
    def delete_temporary_on_failure(self) -> bool:
        return bool(self._policy.get("delete_temporary_on_failure", False))
    
    @property
    def preserve_finalization_evidence(self) -> bool:
        return bool(self._policy.get("preserve_finalization_evidence", True))
    
    @property
    def preserve_active_references(self) -> bool:
        return bool(self._policy.get("preserve_active_references", True))
    
    @property
    def dry_run_default(self) -> bool:
        return bool(self._policy.get("dry_run_default", True))
    
    def to_dict(self) -> dict[str, Any]:
        """Return policy as dictionary."""
        return self._policy.copy()


def load_policy(policy_path: str | None = None) -> RetentionPolicy:
    """Load retention policy from file or return defaults."""
    import json
    from pathlib import Path
    
    if policy_path:
        path = Path(policy_path)
        if path.exists():
            with open(path, 'r') as f:
                policy_data = json.load(f)
            return RetentionPolicy(policy_data)
    
    return RetentionPolicy()
