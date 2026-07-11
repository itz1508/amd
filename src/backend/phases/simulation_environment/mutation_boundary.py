"""Mutation boundary management."""
import fnmatch
import hashlib
from pathlib import Path
from typing import Any

from .schema import Apply_Mutation_Boundary, Target_Mutation, Changed_File, Change_Type
from .validator import (
    validate_mutation_boundary,
    validate_file_count_boundary,
    validate_bytes_boundary,
)
from .errors import (
    MutationBoundaryError,
    ForbiddenPathError,
    UndeclaredFileError,
    MaxFilesExceededError,
    MaxBytesExceededError,
)


def create_mutation_boundary(
    admitted_package_plan: dict[str, Any],
    supporting_metadata: dict[str, Any],
) -> Apply_Mutation_Boundary:
    """Create mutation boundary from admitted package plan.
    
    Before isolated mutation, define:
    - allowed files
    - allowed paths
    - forbidden paths
    - allowed commands
    - maximum files changed
    - maximum total bytes written
    - admitted package-plan operations
    - rollback evidence
    
    Args:
        admitted_package_plan: Admitted package plan
        supporting_metadata: Supporting metadata
        
    Returns:
        Apply_Mutation_Boundary with defined constraints
    """
    # Extract allowed files from package plan
    allowed_files = admitted_package_plan.get("allowed_files", [])
    if not allowed_files:
        # Default allowed files
        allowed_files = [
            "*.py",
            "*.json",
            "*.yaml",
            "*.yml",
            "*.toml",
            "*.txt",
            "*.md",
        ]
    
    # Extract allowed paths
    allowed_paths = admitted_package_plan.get("allowed_paths", [])
    if not allowed_paths:
        allowed_paths = [
            "src/*",
            "tests/*",
            "*.py",
        ]
    
    # Extract forbidden paths
    forbidden_paths = admitted_package_plan.get("forbidden_paths", [])
    default_forbidden = [
        ".git/*",
        "*.lock",
        "node_modules/*",
        ".venv/*",
        "venv/*",
        "__pycache__/*",
        "*.pyc",
        ".env",
        "*.env",
        "credentials*",
        "secrets*",
    ]
    forbidden_paths = list(set(forbidden_paths + default_forbidden))
    
    # Extract allowed commands
    allowed_commands = admitted_package_plan.get("allowed_commands", [])
    if not allowed_commands:
        allowed_commands = [
            "python",
            "pip",
            "uv",
            "pytest",
            "echo",
            "cat",
            "head",
            "tail",
            "grep",
            "sed",
            "awk",
        ]
    
    # Extract limits
    max_files_changed = admitted_package_plan.get("max_files_changed", 10)
    max_bytes_written = admitted_package_plan.get("max_bytes_written", 1024 * 1024)  # 1MB
    
    # Extract admitted operations
    admitted_operations = admitted_package_plan.get("operations", [])
    
    # Create boundary
    boundary = Apply_Mutation_Boundary(
        allowed_files=list(allowed_files),
        allowed_paths=list(allowed_paths),
        forbidden_paths=list(forbidden_paths),
        allowed_commands=list(allowed_commands),
        max_files_changed=max_files_changed,
        max_bytes_written=max_bytes_written,
        admitted_package_plan_operations=list(admitted_operations),
        rollback_evidence={
            "strategy": "copy_on_write",
            "backup_location": "backup",
        },
        metadata={
            "source": "admitted_package_plan",
        },
    )
    
    return boundary


def check_file_within_boundary(
    boundary: Apply_Mutation_Boundary,
    file_path: str | Path,
) -> bool:
    """Check if a file path is within the mutation boundary.
    
    Args:
        boundary: Mutation boundary
        file_path: File path to check (relative)
        
    Returns:
        True if within boundary
        
    Raises:
        MutationBoundaryError: if file is outside boundary
    """
    file_str = str(file_path)
    
    # Normalize path
    file_str = file_str.replace("\\", "/")
    
    # Check against boundary
    validate_mutation_boundary(boundary.to_dict(), file_str)
    
    return True


def create_target_mutation(
    boundary: Apply_Mutation_Boundary,
    description: str,
) -> Target_Mutation:
    """Create a target mutation record.
    
    Args:
        boundary: Mutation boundary
        description: Description of mutation
        
    Returns:
        Target_Mutation ready for recording changes
    """
    mutation_id = f"mutation-{hash(description) % 1000000:06d}"
    
    return Target_Mutation(
        mutation_id=mutation_id,
        description=description,
        changed_files=[],
        command_output="",
        structured_errors=[],
        metadata={
            "boundary_id": boundary.metadata.get("id", ""),
        },
    )


def record_file_change(
    mutation: Target_Mutation,
    file_path: str,
    change_type: Change_Type,
    before_content: bytes | None = None,
    after_content: bytes | None = None,
) -> Changed_File:
    """Record a file change in a mutation.
    
    Args:
        mutation: Target mutation to record in
        file_path: Path of changed file (relative)
        change_type: Type of change
        before_content: Content before change
        after_content: Content after change
        
    Returns:
        Changed_File record
    """
    before_hash = hashlib.sha256(before_content or b"").hexdigest() if before_content else ""
    after_hash = hashlib.sha256(after_content or b"").hexdigest() if after_content else ""
    bytes_written = len(after_content or b"")
    
    changed_file = Changed_File(
        file_path=file_path.replace("\\", "/"),
        change_type=change_type,
        before_hash=before_hash,
        after_hash=after_hash,
        bytes_written=bytes_written,
        command_output="",
        structured_errors=[],
        metadata={},
    )
    
    mutation.changed_files.append(changed_file)
    
    return changed_file


def validate_mutation_completeness(
    mutation: Target_Mutation,
    boundary: Apply_Mutation_Boundary,
) -> bool:
    """Validate that mutation is complete and within boundaries.
    
    Args:
        mutation: Target mutation
        boundary: Mutation boundary
        
    Returns:
        True if valid
        
    Raises:
        MaxFilesExceededError: if file count exceeded
        MaxBytesExceededError: if bytes exceeded
    """
    file_count = len(mutation.changed_files)
    total_bytes = sum(cf.bytes_written for cf in mutation.changed_files)
    
    validate_file_count_boundary(boundary.to_dict(), file_count)
    validate_bytes_boundary(boundary.to_dict(), total_bytes)
    
    return True
