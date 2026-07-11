from __future__ import annotations

import importlib
import importlib.util
import json
from pathlib import Path
from typing import Any, Dict, List

import jsonschema

from .loader import load_capability_definitions


_REQUIRED_FIELDS = {
    'capability_id',
    'version',
    'task_categories',
    'description',
    'execution_modes',
    'allowed_tools',
    'allowed_validators',
    'allowed_models',
    'input_schema',
    'output_schema',
    'benchmark_suites',
    'deterministic_eligible',
    'supports_batch',
    'timeout_ms',
    'max_retries',
    'owner_module',
    'status',
    'implementation',
}


def _schema_path() -> Path:
    return Path(__file__).resolve().parent / 'schemas' / 'capability-definition.schema.json'


def _load_schema() -> Dict[str, Any]:
    with _schema_path().open('r', encoding='utf-8') as handle:
        return json.load(handle)


def _resolve_module_path(reference: str) -> str:
    """Return the module path portion of a dotted reference.

    ``amd_track1.capabilities.executors.code_debugging`` -> ``amd_track1.capabilities.executors``
    """
    parts = reference.split('.')
    for index in range(len(parts), 0, -1):
        candidate = '.'.join(parts[:index])
        try:
            if importlib.util.find_spec(candidate) is not None:
                return candidate
        except (AttributeError, ModuleNotFoundError, ValueError):
            continue
    return reference


def _is_reachable(reference: str) -> bool:
    """Return True if ``reference`` resolves to an importable module or attribute."""
    module_path = _resolve_module_path(reference)
    try:
        if importlib.util.find_spec(module_path) is None:
            return False
    except (AttributeError, ModuleNotFoundError, ValueError):
        return False
    if module_path == reference:
        return True
    # Try to import the parent module and look up the attribute.
    try:
        module = importlib.import_module(module_path)
    except Exception:
        return False
    attribute = reference[len(module_path) + 1:]
    if not attribute:
        return True
    parts = attribute.split('.')
    current: Any = module
    for part in parts:
        if not hasattr(current, part):
            return False
        current = getattr(current, part)
    return True


def validate_definition(definition: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    capability_id = definition.get('capability_id') or '<unknown>'

    try:
        jsonschema.validate(instance=definition, schema=_load_schema())
    except jsonschema.ValidationError as exc:
        errors.append(f'schema validation error: {exc.message}')

    missing = _REQUIRED_FIELDS - set(definition.keys())
    if missing:
        errors.append(f'missing fields: {sorted(missing)}')
    if not definition.get('capability_id'):
        errors.append('capability_id is required')
    if not definition.get('task_categories'):
        errors.append('task_categories is required')

    implementation = definition.get('implementation')
    if not implementation:
        errors.append('implementation is required')
    elif not _is_reachable(implementation):
        errors.append(f'implementation is unreachable: {implementation}')

    owner_module = definition.get('owner_module')
    if owner_module and not _is_reachable(owner_module):
        errors.append(f'owner_module is unreachable: {owner_module}')

    if definition.get('status') not in {'active', 'experimental', 'deprecated'}:
        errors.append('status must be active, experimental, or deprecated')

    if definition.get('deterministic_eligible') is None:
        errors.append('deterministic_eligible is required')

    allowed_tools = definition.get('allowed_tools', [])
    allowed_validators = definition.get('allowed_validators', [])
    if not allowed_tools and not allowed_validators:
        errors.append('at least one allowed tool or validator is required')

    return [f'{capability_id}: {error}' for error in errors]


def validate_registry() -> List[str]:
    errors: List[str] = []
    definitions = load_capability_definitions()
    seen_ids: set[str] = set()
    for definition in definitions:
        capability_id = definition.get('capability_id')
        if capability_id in seen_ids:
            errors.append(f'duplicate capability_id: {capability_id}')
        if capability_id:
            seen_ids.add(capability_id)
        errors.extend(validate_definition(definition))
    return sorted(errors)
