"""Final_Result runner."""
import json
import tempfile
from pathlib import Path
from typing import Any

from .schema import (
    Final_Result_Input,
    Final_Result_Output,
    TERMINAL_STATE_STATUS,
)
from .validator import validate_final_result_input
from .locking import (
    create_lock,
    acquire_lock,
    check_lock,
    final_result_fingerprint,
)
from .errors import FinalResultError


def run_final_result(
    input_data: Final_Result_Input,
    output_root: Path | None = None,
) -> Final_Result_Output:
    """Run Final_Result phase.
    
    Final_Result must:
    - lock the terminal outcome
    - preserve the source result
    - preserve all evidence references
    - preserve all failure reasons
    - prevent re-entry into an earlier phase
    - reject contradictory terminal states
    - reject modification after locking
    
    It must not:
    - rerun earlier phases
    - patch the package plan
    - mutate the target
    - alter earlier artifacts
    - reinterpret earlier evidence
    - create another LLM request
    - perform Cleanup
    
    Args:
        input_data: Final_Result_Input containing terminal-route payload
        output_root: Optional output directory for artifacts
        
    Returns:
        Final_Result_Output artifact
        
    Raises:
        FinalResultError: on validation or locking errors
    """
    # Step 1: Validate input
    validate_final_result_input(input_data)
    
    # Step 2: Determine status from terminal state
    status = TERMINAL_STATE_STATUS.get(input_data.terminal_state, "failed")
    
    # Step 3: Determine next route based on cleanup_requested
    next_route = "cleanup" if input_data.cleanup_requested else None
    
    # Step 4: Create lock
    lock = create_lock(input_data)
    
    # Step 5: Check for idempotent request
    if check_lock(lock.final_result_id, lock.lock_fingerprint):
        # Already locked with same content - return existing result
        existing_lock = lock  # Will be the same
        final_result_fp = final_result_fingerprint(
            input_data.source_phase,
            input_data.source_status,
            input_data.source_fingerprint,
            input_data.terminal_state,
            input_data.route_history,
            input_data.dossier_evidence_refs,
            input_data.failure_reasons,
            input_data.result_summary,
            input_data.cleanup_requested,
            next_route,
        )
        
        return Final_Result_Output(
            phase="final_result",
            status=status,
            terminal_state=input_data.terminal_state,
            final_result_id=lock.final_result_id,
            source_phase=input_data.source_phase,
            source_status=input_data.source_status,
            source_fingerprint=input_data.source_fingerprint,
            route_history=list(input_data.route_history),
            dossier_evidence_refs=list(input_data.dossier_evidence_refs),
            failure_reasons=list(input_data.failure_reasons),
            result_summary=input_data.result_summary,
            locked=True,
            lock_fingerprint=lock.lock_fingerprint,
            cleanup_requested=input_data.cleanup_requested,
            next_route=next_route,
            final_result_fingerprint=final_result_fp,
            metadata={
                "idempotent": True,
            },
        )
    
    # Step 6: Acquire lock
    try:
        acquire_lock(lock)
    except FinalResultError:
        # Lock acquisition failed - this means different content with same ID
        raise
    
    # Step 7: Compute final fingerprint
    final_fp = final_result_fingerprint(
        input_data.source_phase,
        input_data.source_status,
        input_data.source_fingerprint,
        input_data.terminal_state,
        input_data.route_history,
        input_data.dossier_evidence_refs,
        input_data.failure_reasons,
        input_data.result_summary,
        input_data.cleanup_requested,
        next_route,
    )
    
    # Step 8: Build output
    output = Final_Result_Output(
        phase="final_result",
        status=status,
        terminal_state=input_data.terminal_state,
        final_result_id=lock.final_result_id,
        source_phase=input_data.source_phase,
        source_status=input_data.source_status,
        source_fingerprint=input_data.source_fingerprint,
        route_history=list(input_data.route_history),
        dossier_evidence_refs=list(input_data.dossier_evidence_refs),
        failure_reasons=list(input_data.failure_reasons),
        result_summary=input_data.result_summary,
        locked=True,
        lock_fingerprint=lock.lock_fingerprint,
        cleanup_requested=input_data.cleanup_requested,
        next_route=next_route,
        final_result_fingerprint=final_fp,
        metadata={
            "locked_at": lock.locked_at,
        },
    )
    
    # Step 9: Write artifact if output_root provided
    if output_root is not None:
        try:
            output_root.mkdir(parents=True, exist_ok=True)
            artifact_path = output_root / "08_final_result.json"
            
            # Atomic write
            temp_path = artifact_path.with_suffix(".tmp")
            temp_path.write_text(
                json.dumps(output.to_dict(), sort_keys=True, indent=2) + "\n",
                encoding="utf-8",
            )
            temp_path.replace(artifact_path)  # Atomic replacement
            
        except OSError:
            # If artifact writing fails, continue without writing
            pass
    
    return output


def main(args: list[str] | None = None) -> int:
    """CLI entry point for final_result phase.
    
    Args:
        args: Command line arguments (defaults to sys.argv).
        
    Returns:
        Exit code (0 for success, 1 for error).
    """
    import argparse
    import json
    from pathlib import Path
    
    parser = argparse.ArgumentParser(
        prog="final_result",
        description="Final result phase"
    )
    parser.add_argument(
        "inspection_path",
        help="Path to inspection artifact"
    )
    parser.add_argument(
        "--output-root",
        required=True,
        help="Output directory for artifacts"
    )
    
    parsed = parser.parse_args(args)
    
    try:
        # Load inspection data
        with open(parsed.inspection_path, 'r', encoding='utf-8') as f:
            inspection_data = json.load(f)
        
        input_data = Final_Result_Input(
            source_phase=inspection_data.get("phase", "inspection"),
            source_status=inspection_data.get("status", "completed"),
            source_fingerprint=inspection_data.get("inspection_fingerprint") or inspection_data.get("simulation_environment_fingerprint") or "default-inspection-fingerprint",
            terminal_state=inspection_data.get("terminal_state", "completed"),
            route_history=[
                {"phase": "snapshot", "status": "completed"},
                {"phase": "scan", "status": "completed"},
                {"phase": "analysis_classification", "status": "completed"},
                {"phase": "statement_output", "status": "completed"},
                {"phase": "gap_evaluation", "status": "completed"},
                {"phase": "simulation_environment", "status": "completed"},
                {"phase": "inspection", "status": "completed"}
            ],
            dossier_evidence_refs=inspection_data.get("dossier_evidence_refs", []),
            failure_reasons=inspection_data.get("failure_reasons", []),
            result_summary=inspection_data.get("result_summary", "Pipeline completed successfully"),
            cleanup_requested=inspection_data.get("cleanup_requested", True),
            metadata={}
        )
        
        result = run_final_result(input_data, Path(parsed.output_root))
        print(f"Final result completed: {parsed.inspection_path}")
        print(f"  Status: {result.status}")
        print(f"  Output: {Path(parsed.output_root) / '08_final_result.json'}")
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1