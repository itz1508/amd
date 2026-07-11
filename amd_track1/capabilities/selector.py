from __future__ import annotations

from typing import Any, Dict, List

from .loader import load_capability_definitions


EXECUTOR_OVERRIDES = {
    "mathematical_reasoning": {"executor_id": "arithmetic_evaluator", "module": "amd_track1.capabilities.executors"},
    "sentiment_classification": {"executor_id": "sentiment_validator", "module": "amd_track1.capabilities.executors"},
    "text_summarisation": {"executor_id": "summary_validator", "module": "amd_track1.capabilities.executors"},
    "named_entity_recognition": {"executor_id": "ner_validator", "module": "amd_track1.capabilities.executors"},
    "code_debugging": {"executor_id": "code_checker", "module": "amd_track1.capabilities.executors"},
    "logical_reasoning": {"executor_id": "logic_checker", "module": "amd_track1.capabilities.executors"},
    "code_generation": {"executor_id": "code_generator", "module": "amd_track1.capabilities.executors"},
    "factual_knowledge": {"executor_id": "factual_lookup", "module": "amd_track1.capabilities.executors"},
}


def find_capabilities(task_category: str) -> List[Dict[str, Any]]:
    definitions = load_capability_definitions()
    return [definition for definition in definitions if task_category in definition.get("task_categories", [])]


def resolve_executor(capability_id: str) -> Dict[str, Any] | None:
    capability = next((item for item in load_capability_definitions() if item.get("capability_id") == capability_id), None)
    if capability is None:
        return None
    executor = EXECUTOR_OVERRIDES.get(capability_id, {"executor_id": capability.get("capability_id"), "module": capability.get("implementation")})
    return {"capability_id": capability_id, **executor}


def resolve_validators(capability_id: str) -> List[str]:
    capability = next((item for item in load_capability_definitions() if item.get("capability_id") == capability_id), None)
    if capability is None:
        return []
    return capability.get("allowed_validators", [])


def list_benchmark_suites(capability_id: str) -> List[str]:
    capability = next((item for item in load_capability_definitions() if item.get("capability_id") == capability_id), None)
    if capability is None:
        return []
    return capability.get("benchmark_suites", [])
