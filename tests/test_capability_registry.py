from pathlib import Path

from amd_track1.capabilities import (
    find_capabilities,
    get_capability,
    list_capabilities,
    resolve_executor,
    resolve_validators,
    validate_registry,
)


def test_registry_exposes_active_capabilities() -> None:
    capabilities = list_capabilities()
    assert len(capabilities) >= 8
    assert any(item["capability_id"] == "mathematical_reasoning" for item in capabilities)

    capability = get_capability("mathematical_reasoning")
    assert capability is not None
    assert capability["status"] == "active"
    assert capability["deterministic_eligible"] is True

    matched = find_capabilities("mathematical_reasoning")
    assert matched and matched[0]["capability_id"] == "mathematical_reasoning"

    executor = resolve_executor("mathematical_reasoning")
    assert executor is not None
    assert executor["executor_id"] == "arithmetic_evaluator"

    validators = resolve_validators("mathematical_reasoning")
    assert validators

    errors = validate_registry()
    assert errors == []


def test_registry_definitions_have_reachable_implementation() -> None:
    capability = get_capability("code_debugging")
    assert capability is not None
    assert capability["owner_module"].startswith("amd_track1")
    assert capability["implementation"] == "amd_track1.capabilities.executors.code_debugging"
