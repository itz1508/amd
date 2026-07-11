"""
Canonical phase order definition.
"""

Phase_order = (
    "snapshot",
    "scan",
    "analysis_classification",
    "statement_output",
    "gap_evaluation",
    "simulation_environment",
    "inspection",
    "final_result",
    "cleanup",
)

# Internal stages of simulation_environment
Simulation_environment_stages = (
    "isolated_runtime_environment",
    "self_contained_runtime_demo",
    "execution",
)

# Internal stages of execution
Execution_stages = (
    "apply_mutation_boundary",
    "target_mutation",
    "post_apply_verification",
)