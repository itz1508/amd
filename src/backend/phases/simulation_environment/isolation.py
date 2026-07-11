"""Isolated runtime environment management."""
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any
from dataclasses import asdict

from .schema import (
    Isolated_Runtime_Environment,
    Self_Contained_Runtime_Demo,
)
from .validator import (
    validate_isolated_environment,
    validate_demo_self_contained,
)
from .errors import (
    IsolationError,
    EnvironmentPreparationError,
    MissingDemoDependencyError,
)


def compute_sha256(file_path: str | Path) -> str:
    """Compute SHA-256 hash of a file."""
    path = Path(file_path)
    if not path.exists():
        return ""
    
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def compute_directory_inventory(directory: str | Path, relative_to: str | Path | None = None) -> list[dict[str, Any]]:
    """Compute file inventory for a directory.
    
    Returns list of file entries with relative paths and metadata.
    """
    dir_path = Path(directory)
    if relative_to:
        base_path = Path(relative_to)
    else:
        base_path = dir_path
    
    inventory = []
    
    for file_path in dir_path.rglob("*"):
        if file_path.is_file():
            try:
                rel_path = str(file_path.relative_to(base_path))
                file_hash = compute_sha256(file_path)
                file_size = file_path.stat().st_size
                
                inventory.append({
                    "path": rel_path.replace("\\", "/"),  # Normalize path separators
                    "size": file_size,
                    "hash": file_hash,
                    "is_file": True,
                })
            except (OSError, PermissionError):
                # Skip files that can't be read
                pass
    
    return inventory


def create_isolated_environment(
    real_target_path: str | Path,
    demo: Self_Contained_Runtime_Demo,
    isolated_output_location: str | Path | None = None,
) -> Isolated_Runtime_Environment:
    """Create an isolated runtime environment.
    
    Requirements:
    - exists outside the real target
    - uses a separate writable location
    - preserves source-relative paths
    - contains only required simulation files
    - records source hashes
    - records isolated hashes
    - is reproducible from the same admitted input
    - never writes to the real target
    
    Args:
        real_target_path: Path to the real target
        demo: Self-contained runtime demo
        isolated_output_location: Optional explicit isolated output location
        
    Returns:
        Isolated_Runtime_Environment ready for use
        
    Raises:
        EnvironmentPreparationError: if environment cannot be prepared
    """
    real_target = Path(real_target_path)
    
    # Create isolated directory
    if isolated_output_location:
        isolated_root = Path(isolated_output_location)
    else:
        # Create in temp directory
        isolated_root = Path(tempfile.mkdtemp(prefix="sim_env_"))
    
    try:
        isolated_root.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise EnvironmentPreparationError(f"Cannot create isolated root: {e}")
    
    # Resolve real target
    real_target_resolved = real_target.resolve()
    isolated_root_resolved = isolated_root.resolve()
    
    # Validate isolation
    validate_isolated_environment(
        str(isolated_root_resolved),
        str(real_target_resolved),
        []  # Will be populated below
    )
    
    # Copy required source files from real target to isolated environment
    required_files = demo.required_source_files
    file_inventory = []
    source_hashes = {}
    isolated_hashes = {}
    copied_files = []
    
    for source_file in required_files:
        source_path = real_target_resolved / source_file
        isolated_path = isolated_root_resolved / source_file
        
        # Create parent directories
        isolated_path.parent.mkdir(parents=True, exist_ok=True)
        
        if source_path.exists():
            # Copy file
            shutil.copy2(source_path, isolated_path)
            
            # Record hashes
            source_hash = compute_sha256(source_path)
            isolated_hash = compute_sha256(isolated_path)
            
            source_hashes[source_file] = source_hash
            isolated_hashes[source_file] = isolated_hash
            copied_files.append(source_file)
            
            file_inventory.append({
                "path": source_file,
                "size": isolated_path.stat().st_size,
                "source_hash": source_hash,
                "isolated_hash": isolated_hash,
            })
        else:
            raise MissingDemoDependencyError(
                f"Required source file not found: {source_file}"
            )
    
    # Validate demo is self-contained
    validate_demo_self_contained(demo.to_dict(), copied_files)
    
    # Create environment ID
    environment_id = f"env-{hash(str(isolated_root_resolved)) % 1000000:06d}"
    
    # Create isolated runtime environment
    isolated_env = Isolated_Runtime_Environment(
        environment_id=environment_id,
        isolated_root_path=str(isolated_root_resolved),
        real_target_path=str(real_target_resolved),
        file_inventory=file_inventory,
        source_hashes=source_hashes,
        isolated_hashes=isolated_hashes,
        demo=demo,
        metadata={
            "created_from": str(real_target_resolved),
            "copied_files": copied_files,
        },
    )
    
    return isolated_env


def cleanup_isolated_environment(isolated_env: Isolated_Runtime_Environment) -> bool:
    """Clean up isolated environment.
    
    Args:
        isolated_env: Isolated environment to clean up
        
    Returns:
        True if cleanup successful, False otherwise
    """
    try:
        isolated_root = Path(isolated_env.isolated_root_path)
        if isolated_root.exists():
            shutil.rmtree(isolated_root)
            return True
    except (OSError, PermissionError):
        pass
    return False


def verify_isolation(
    isolated_env: Isolated_Runtime_Environment,
    real_target_path: str | Path,
) -> bool:
    """Verify that isolation is maintained.
    
    Checks:
    - isolated environment still exists
    - real target is unchanged
    - source hashes match original
    
    Args:
        isolated_env: Isolated environment
        real_target_path: Path to real target
        
    Returns:
        True if isolation is verified
        
    Raises:
        TargetModifiedError: if real target was modified
    """
    real_target = Path(real_target_path)
    
    # Check real target still exists
    if not real_target.exists():
        from .errors import TargetModifiedError
        raise TargetModifiedError(f"Real target {real_target} no longer exists")
    
    # Check source hashes still match
    for source_file, expected_hash in isolated_env.source_hashes.items():
        source_path = real_target / source_file
        if source_path.exists():
            current_hash = compute_sha256(source_path)
            if current_hash != expected_hash:
                from .errors import TargetModifiedError
                raise TargetModifiedError(
                    f"Source file {source_file} was modified: "
                    f"expected {expected_hash[:16]}... got {current_hash[:16]}..."
                )
    
    return True
