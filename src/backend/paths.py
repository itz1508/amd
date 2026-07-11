"""
Target and output path resolution for snapshot phase.

Canonical shared module for the backend namespace.
Provides path resolution and output boundary enforcement
required by the filesystem Snapshot phase.
"""
from pathlib import Path
import os


class OutputBoundaryError(Exception):
    """Error when output would be inside target directory."""
    pass


def resolve_target(target: str | Path) -> Path:
    """Resolve and validate target path.

    Args:
        target: Target path as string or Path object.

    Returns:
        Resolved absolute Path to target directory.

    Raises:
        ValueError: If target does not exist or is not a directory.
    """
    target_path = Path(target).resolve()
    if not target_path.exists():
        raise ValueError(f"Target path does not exist: {target}")
    if not target_path.is_dir():
        raise ValueError(f"Target path is not a directory: {target}")
    return target_path


def resolve_output_root(output_root: str | Path, target_root: Path) -> Path:
    """Resolve and validate output path with boundary enforcement.

    Args:
        output_root: Output path as string or Path object.
        target_root: Already resolved target path for boundary check.

    Returns:
        Resolved absolute Path to output root.

    Raises:
        OutputBoundaryError: If output_root equals or is inside target_root.
    """
    output_path = Path(output_root).resolve()

    # Check output boundary: must not be inside target
    # Check equality first
    if output_path == target_root:
        raise OutputBoundaryError(
            f"Output root cannot equal target root: {output_root}"
        )

    try:
        output_path.relative_to(target_root)
        # output_path is inside target_root
        raise OutputBoundaryError(
            f"Output root cannot be inside target root: {output_root}"
        )
    except ValueError:
        pass  # output_path is not inside target_root - this is correct

    return output_path


def get_default_output_root() -> Path:
    """Get the default output root path."""
    return Path(os.getcwd()).resolve()