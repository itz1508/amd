"""
Canonical transition specification.
"""

Transition_table = {
    "statement_output": {
        "next": "gap_evaluation",
    },
    "gap_evaluation": {
        "attempt_1": {
            "valid": {
                "next": "simulation_environment",
            },
            "not_valid": {
                "next": "gap_evaluation",
                "action": "package_plan_correction",
            },
        },
        "attempt_2": {
            "valid": {
                "next": "simulation_environment",
            },
            "not_valid": {
                "next": "gap_handoff",
            },
        },
    },
    "gap_handoff": {
        "next": None,
        "terminal_state": "operator_action_required",
    },
    "simulation_environment": {
        "ready": {
            "next": "execution",
        },
        "failure": {
            "next": "final_result",
            "terminal_state": "failed_simulation_environment",
        },
    },
    "execution": {
        "success": {
            "next": "inspection",
        },
        "failure": {
            "next": "gap_handoff",
        },
    },
    "inspection": {
        "success": {
            "next": "final_result",
        },
        "failure": {
            "next": "final_result",
            "terminal_state": "failed_inspection",
        },
    },
    "final_result": {
        "next": {
            "cleanup_requested": "cleanup",
            "cleanup_not_requested": None,
        },
    },
    "cleanup": {
        "next": None,
    },
}
