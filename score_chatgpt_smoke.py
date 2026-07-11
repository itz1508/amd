#!/usr/bin/env python3
"""Score ChatGPT 19-case smoke results against expected answers."""

import json
import sys

EXPECTED = {
    "mix-001": {"category": "mathematical_reasoning", "route": "deterministic", "answer": "69"},
    "mix-002": {"category": "mathematical_reasoning", "route": "deterministic", "answer": "30"},
    "mix-003": {"category": "mathematical_reasoning", "route": "deterministic", "answer": "6"},
    "mix-004": {"category": "sentiment_classification", "route": "fireworks", "answer": "positive"},
    "mix-005": {"category": "sentiment_classification", "route": "fireworks", "answer": "neutral"},
    "mix-006": {"category": "named_entity_recognition", "route": "fireworks", "answer": None},  # entities check
    "mix-007": {"category": "named_entity_recognition", "route": "fireworks", "answer": None},
    "mix-008": {"category": "text_summarisation", "route": "fireworks", "answer": None},  # required_facts check
    "mix-009": {"category": "text_summarisation", "route": "fireworks", "answer": None},
    "mix-010": {"category": "code_debugging", "route": "fireworks", "answer": None},  # code properties
    "mix-011": {"category": "code_debugging", "route": "fireworks", "answer": None},
    "mix-012": {"category": "code_generation", "route": "fireworks", "answer": None},  # code properties
    "mix-013": {"category": "code_generation", "route": "fireworks", "answer": None},
    "mix-014": {"category": "logical_reasoning", "route": "fireworks", "answer_prefix": "no"},
    "mix-015": {"category": "logical_reasoning", "route": "fireworks", "answer": "A"},
    "mix-016": {"category": "logical_reasoning", "route": "fireworks", "answer": "no"},
    "mix-017": {"category": "factual_knowledge", "route": "fireworks", "answer": "HTTPS"},
    "mix-018": {"category": "factual_knowledge", "route": "fireworks", "answer": None},  # required_facts
    "mix-019": {"category": "code_debugging", "route": "fireworks", "answer": None},  # required_facts
}

def load_results(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def score():
    results = load_results(r"D:\Dev\amd\temp_container_output\results.json")
    results_map = {r["task_id"]: r for r in results}

    scores = {
        "category_accuracy": 0,
        "route_accuracy": 0,
        "answer_correctness": 0,
        "schema_integrity": 0,
        "id_order_integrity": 0,
        "no_unnecessary_remote": 0,
    }

    # We don't have category/route in results.json (only task_id + answer)
    # So we score what we can from the output file
    total = 19
    deterministic_tasks = {"mix-001", "mix-002", "mix-003"}

    # Schema integrity: every result has task_id and answer
    for r in results:
        if "task_id" in r and "answer" in r:
            scores["schema_integrity"] += 1

    # ID/order integrity: check all expected IDs present
    found_ids = {r["task_id"] for r in results}
    expected_ids = set(EXPECTED.keys())
    scores["id_order_integrity"] = len(found_ids & expected_ids)

    # Answer correctness for tasks with exact expected answers
    exact_answer_tasks = ["mix-001", "mix-002", "mix-003", "mix-004", "mix-005",
                          "mix-015", "mix-016", "mix-017"]
    for tid in exact_answer_tasks:
        if tid in results_map:
            ans = results_map[tid]["answer"]
            expected_ans = EXPECTED[tid].get("answer") or EXPECTED[tid].get("answer_prefix")
            if expected_ans and expected_ans.lower() in ans.lower():
                scores["answer_correctness"] += 1

    # Prefix checks
    for tid in ["mix-014"]:
        if tid in results_map:
            ans = results_map[tid]["answer"]
            if ans.lower().startswith("no"):
                scores["answer_correctness"] += 1

    # No unnecessary remote on deterministic tasks
    for tid in deterministic_tasks:
        if tid in results_map:
            ans = results_map[tid]["answer"]
            expected = EXPECTED[tid]["answer"]
            if ans == expected:
                scores["no_unnecessary_remote"] += 1

    # Category/route accuracy can't be scored from results.json alone (no metadata)
    # Mark as N/A for now
    print("=" * 60)
    print("CHATGPT 19-CASE SMOKE SCORECARD")
    print("=" * 60)
    print(f"Total tasks expected: {total}")
    print(f"Tasks returned:       {len(results)}")
    print()
    print("Scorable from results.json:")
    print(f"  Schema integrity (task_id + answer keys):     {scores['schema_integrity']}/{len(results)}")
    print(f"  ID/order integrity (expected IDs present):    {scores['id_order_integrity']}/{total}")
    print(f"  Answer correctness (exact/prefix matches):  {scores['answer_correctness']}/{len(exact_answer_tasks)+1}")
    print(f"  No unnecessary remote (deterministic tasks):  {scores['no_unnecessary_remote']}/3")
    print()
    print("NOT scorable from results.json (need routing metadata):")
    print(f"  Category accuracy: N/A")
    print(f"  Route accuracy:    N/A")
    print()
    print("Per-task results:")
    for tid in sorted(EXPECTED.keys()):
        r = results_map.get(tid)
        if r:
            ans = r["answer"]
            ok = "OK" if (tid in deterministic_tasks and ans == EXPECTED[tid]["answer"]) or \
                 (tid in exact_answer_tasks and EXPECTED[tid].get("answer") and EXPECTED[tid]["answer"].lower() in ans.lower()) or \
                 (tid == "mix-014" and ans.lower().startswith("no")) else "WARN"
            print(f"  {tid}: {ok} {ans[:80]}{'...' if len(ans)>80 else ''}")
        else:
            print(f"  {tid}: MISSING")
    print("=" * 60)

if __name__ == "__main__":
    score()