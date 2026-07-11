"""
Pipeline runner - foundation only.

Canonical structure and routing defined here. Phase behavior implemented
during later migration tasks.
"""

from backend.pipeline.phase_order import Phase_order
from backend.pipeline.transitions import Transition_table
from backend.pipeline.terminal_states import Terminal_states


def get_phase_order() -> tuple[str, ...]:
    """Return the canonical phase order."""
    return Phase_order


def get_transition_table() -> dict:
    """Return the canonical transition table."""
    return Transition_table


def get_terminal_states() -> dict[str, str]:
    """Return the terminal states definition."""
    return Terminal_states