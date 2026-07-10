"""
AMD_REMOTE_MODE policy module.

Provides the three remote modes required for Track 1 submission:
- off:     no Fireworks calls allowed
- rescue:  local/deterministic first; Fireworks only on failure or high-risk
- always:  Fireworks as primary (debug only)

Default final mode is 'rescue'.
"""

import os
from typing import Literal


def get_remote_mode() -> Literal["off", "rescue", "always"]:
    """
    Read AMD_REMOTE_MODE from environment.

    Returns:
        One of 'off', 'rescue', 'always'. Defaults to 'rescue'.
    """
    mode = os.environ.get("AMD_REMOTE_MODE", "rescue").strip().lower()
    if mode in ("off", "0", "false", "no", "none"):
        return "off"
    if mode in ("always", "1", "true", "yes", "force"):
        return "always"
    # Default and any unknown value → rescue
    return "rescue"


def is_remote_allowed() -> bool:
    """Return True if Fireworks remote calls are permitted."""
    return get_remote_mode() != "off"


def is_rescue_mode() -> bool:
    """Return True if we are in rescue mode (local-first, remote on failure)."""
    return get_remote_mode() == "rescue"


def is_always_remote() -> bool:
    """Return True if remote is the primary path (debug mode)."""
    return get_remote_mode() == "always"