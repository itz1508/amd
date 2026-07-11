"""Run context utilities for AMD phases."""
import os
from datetime import datetime, timezone
from pathlib import Path
import uuid


def generate_run_id() -> str:
    """Generate a unique run identifier."""
    return str(uuid.uuid4())


def get_created_at_iso() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()
