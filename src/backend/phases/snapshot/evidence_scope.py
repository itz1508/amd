"""
Evidence scope rules for snapshot capture.
"""
from dataclasses import dataclass
from pathlib import Path


EXCLUDED_DIRECTORY_NAMES = {
    ".agents",
    ".codex",
    ".git",
    ".kiro",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    ".workbench-venv",
    "__pycache__",
    "env",
    "input",
    "node_modules",
    "output",
    "package",
    "runs",
    "venv",
    "workbench-venv",
}

EXCLUDED_FILE_NAMES = {
    ".env",
    ".env.backup",
    "ollamasetup.exe",
}


@dataclass(frozen=True)
class ScopeDecision:
    included: bool
    reason: str


def evaluate_evidence_path(path: Path, *, is_dir: bool) -> ScopeDecision:
    """Return whether a path belongs in target evidence capture."""
    name = path.name
    normalized_name = name.lower()

    if is_dir:
        if name in EXCLUDED_DIRECTORY_NAMES or normalized_name in EXCLUDED_DIRECTORY_NAMES:
            return ScopeDecision(False, f"Directory excluded: {name}")
        return ScopeDecision(True, "Directory included")

    if name in EXCLUDED_FILE_NAMES or normalized_name in EXCLUDED_FILE_NAMES:
        return ScopeDecision(False, f"File excluded: {name}")

    return ScopeDecision(True, "File included")
