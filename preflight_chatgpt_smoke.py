#!/usr/bin/env python3
"""Zero-token preflight for ChatGPT smoke set (mix-001..019)."""

import json
import os
import sys

# Ensure amd_track1 is importable
sys.path.insert(0, r"D:\Dev\amd")

from amd_track1.classifier import TaskClassifier
from amd_track1.model_registry import ModelRegistry
from amd_track1.router import TaskRouter


def main():
    with open(r"C:\Users\itz15\.codex\attachments\7cff162c-9e70-4086-a85d-da0a3748a8e4\pasted-text.txt", "r", encoding="utf-8") as f:
        tasks = json.load(f)

    classifier = TaskClassifier()
    registry = ModelRegistry()
    registry.initialize("fake-model")
    router = TaskRouter()
    router._registry = registry

    print("=" * 70)
    print("ChatGPT Smoke Preflight (zero-token)")
    print("=" * 70)

    issues = []
    for task in tasks:
        tid = task["task_id"]
        prompt = task["prompt"]
        expected_cat = task.get("expected_category")
        expected_route = task.get("expected_route")

        classification = classifier.classify(tid, prompt)
        category = classification["category"]

        decision = router.route_task({"task_id": tid, "prompt": prompt})
        route = "deterministic" if decision.selected_model is None and "tool" in decision.routing_reason else "fireworks"

        status = "OK"
        if expected_cat and category != expected_cat:
            status = f"CAT_MISMATCH (expected {expected_cat}, got {category})"
            issues.append(f"{tid}: {status}")
        if expected_route and route != expected_route:
            status = f"ROUTE_MISMATCH (expected {expected_route}, got {route})"
            issues.append(f"{tid}: {status}")

        print(f"{tid:8s} | {category:25s} | {route:13s} | {status}")

    print("=" * 70)
    if issues:
        print(f"ISSUES ({len(issues)}):")
        for i in issues:
            print(f"  - {i}")
    else:
        print("All tasks match expected category and route.")
    print("=" * 70)


if __name__ == "__main__":
    main()