"""
Hashing utilities for snapshot phase.
"""
import hashlib
from pathlib import Path


def compute_sha256(file_path: Path) -> str:
    """Compute SHA-256 hash of a file.
    
    Args:
        file_path: Path to file to hash.
        
    Returns:
        Hexadecimal SHA-256 hash string, or empty string on error.
    """
    sha256 = hashlib.sha256()
    try:
        with file_path.open("rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()
    except (OSError, IOError):
        return ""