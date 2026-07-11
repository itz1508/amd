"""
Terminal states definition.
"""

Terminal_states = {
    "completed": "All phases completed successfully",
    "failed_gap_evaluation": "Gap_Evaluation failed after 2 attempts",
    "operator_action_required": "Gap evidence requires an agent/operator decision before execution phases may run",
    "failed_simulation_environment": "Simulation_Environment preparation failed",
    "failed_execution": "Execution failed",
    "failed_inspection": "Inspection failed",
}
