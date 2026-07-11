#!/usr/bin/env python3
"""Trace deterministic routing for the three math tasks."""

import sys
sys.path.insert(0, r"D:\Dev\amd")

from amd_track1.classifier import TaskClassifier
from amd_track1.model_registry import ModelRegistry
from amd_track1.router import TaskRouter
from amd_track1.executor import TaskExecutor

tasks = [
    {"task_id": "mix-001", "prompt": "Calculate: 15 + 27 * 2"},
    {"task_id": "mix-002", "prompt": "What is 20% of 150?"},
    {"task_id": "mix-003", "prompt": "Calculate: ((8 + 4) * 3 - 6) / 5"},
]

classifier = TaskClassifier()
registry = ModelRegistry()
registry.initialize("fake-model")
router = TaskRouter()
router._registry = registry

print("Router decisions:")
for task in tasks:
    decision = router.route_task(task)
    print(f"  {task['task_id']}: model={decision.selected_model}, reason={decision.routing_reason}")

print("\nExecutor with fake Fireworks:")
import os
os.environ["ALLOWED_MODELS"] = "fake-model"
os.environ["FIREWORKS_API_KEY"] = "fake"
os.environ["FIREWORKS_BASE_URL"] = "http://invalid.test"

executor = TaskExecutor()
executor.initialize("fake-model")

for task in tasks:
    result = executor.execute_task(task)
    print(f"  {task['task_id']}: success={result.success}, answer={result.answer}, model={result.model_used}, error={result.model_error}")