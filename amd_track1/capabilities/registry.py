from __future__ import annotations

from typing import Any, Dict, List

from .loader import load_capability_definitions
from .selector import find_capabilities, list_benchmark_suites, resolve_executor, resolve_validators
from .validation import validate_registry as validate_registry_definitions


def list_capabilities() -> List[Dict[str, Any]]:
    definitions = load_capability_definitions()
    return sorted(definitions, key=lambda item: item.get("capability_id", ""))


def get_capability(capability_id: str) -> Dict[str, Any] | None:
    for definition in list_capabilities():
        if definition.get("capability_id") == capability_id:
            return definition
    return None


def validate_registry() -> List[str]:
    return validate_registry_definitions()


__all__ = [
    "find_capabilities",
    "get_capability",
    "list_benchmark_suites",
    "list_capabilities",
    "resolve_executor",
    "resolve_validators",
    "validate_registry",
]
