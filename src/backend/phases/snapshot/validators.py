"""
Snapshot validators - exclusion detection.
"""
from pathlib import Path


# Generated/dev folders to exclude from capture
EXCLUDED_FOLDERS = {
    ".git",
    ".agents",
    ".codex",
    ".kiro",
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
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}


EXCLUDED_FILES = {
    ".env",
    ".env.backup",
    "ollamasetup.exe",
}


def is_excluded(path: Path) -> bool:
    """Check if path is an excluded folder.
    
    Args:
        path: Path to check.
        
    Returns:
        True if path is an excluded folder or starts with excluded prefix.
    """
    name = path.name
    name_lower = name.lower()
    if name in EXCLUDED_FOLDERS or name_lower in EXCLUDED_FILES:
        return True
    # Check for hidden variants of excluded folders
    if name.startswith(".") and name[1:] in EXCLUDED_FOLDERS:
        return True
    return False
