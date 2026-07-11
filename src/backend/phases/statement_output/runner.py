"""Statement Output runner."""
import hashlib
import json
from pathlib import Path
from typing import Any
from .schema import (
    Raw_Statement,
    Handoff_Statement,
    LLM_Statement,
    Statement_Output_Input,
    Statement_Output_Output,
)
from .validator import validate_raw_handoff_llm_sequence
from .errors import StatementOutputError


def statement_output_fingerprint(
    raw: Raw_Statement,
    handoff: Handoff_Statement,
    llm: LLM_Statement,
    dossier_evidence_refs: list[str],
) -> str:
    """Compute deterministic fingerprint for statement output.

    Derives from stable canonical statement content, identifiers,
    sequence relationships, and evidence references.

    Excludes:
    - run_id
    - created_at
    - timestamps
    - absolute_paths
    - temporary paths
    """
    payload = {
        "raw_statement_id": raw.statement_id,
        "raw_content": json.dumps(raw.content, sort_keys=True, separators=(",", ":")),
        "raw_dossier_evidence_refs": sorted(raw.dossier_evidence_refs),
        "handoff_statement_id": handoff.statement_id,
        "handoff_raw_statement_id": handoff.raw_statement_id,
        "handoff_scope": handoff.scope,
        "handoff_instructions": json.dumps(handoff.instructions, sort_keys=True, separators=(",", ":")),
        "llm_statement_id": llm.statement_id,
        "llm_raw_statement_id": llm.raw_statement_id,
        "llm_handoff_statement_id": llm.handoff_statement_id,
        "llm_advisory_summary": llm.advisory_summary,
        "llm_interpretations": json.dumps(llm.interpretations, sort_keys=True, separators=(",", ":")),
        "dossier_evidence_refs": sorted(dossier_evidence_refs),
        "sequence_chain": [
            raw.statement_id,
            handoff.statement_id,
            llm.statement_id,
        ],
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def build_output_content(
    raw: Raw_Statement,
    handoff: Handoff_Statement,
    llm: LLM_Statement,
) -> dict[str, Any]:
    """Build deterministic output content dict."""
    return {
        "raw_statement": raw.to_dict(),
        "handoff_statement": handoff.to_dict(),
        "llm_statement": llm.to_dict(),
        "sequence": {
            "order": ["raw", "handoff", "llm"],
            "raw_statement_id": raw.statement_id,
            "handoff_statement_id": handoff.statement_id,
            "llm_statement_id": llm.statement_id,
        },
        "advisory_only": True,
    }


def run_statement_output(
    input_data: Statement_Output_Input,
    output_root: Path | None = None,
) -> Statement_Output_Output:
    """Run Statement_Output phase.

    Args:
        input_data: Statement_Output_Input containing Raw, Handoff, LLM statements
        output_root: Optional output directory. Defaults to current directory.

    Returns:
        Statement_Output_Output artifact

    Raises:
        StatementOutputError: on sequence validation failure
    """
    raw = input_data.raw_statement
    handoff = input_data.handoff_statement
    llm = input_data.llm_statement

    validate_raw_handoff_llm_sequence(raw, handoff, llm)

    fp = statement_output_fingerprint(
        raw, handoff, llm, input_data.dossier_evidence_refs
    )
    output_content = build_output_content(raw, handoff, llm)

    statement_output_id = fp
    output = Statement_Output_Output(
        phase="statement_output",
        status="completed",
        statement_output_id=statement_output_id,
        raw_statement_id=raw.statement_id,
        handoff_statement_id=handoff.statement_id,
        llm_statement_id=llm.statement_id,
        dossier_evidence_refs=list(input_data.dossier_evidence_refs),
        statement_output_fingerprint=fp,
        output_content=output_content,
    )

    if output_root is not None:
        try:
            output_root.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        artifact_path = output_root / "04_statement_output.json"
        try:
            artifact_path.write_text(
                json.dumps(output.to_dict(), sort_keys=True, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError:
            pass

    return output


def main(args: list[str] | None = None) -> int:
    """CLI entry point for statement_output phase.
    
    Args:
        args: Command line arguments (defaults to sys.argv).
        
    Returns:
        Exit code (0 for success, 1 for error).
    """
    import argparse
    import json
    from pathlib import Path
    
    parser = argparse.ArgumentParser(
        prog="statement_output",
        description="Statement output phase"
    )
    parser.add_argument(
        "analysis_path",
        help="Path to analysis classification artifact"
    )
    parser.add_argument(
        "--output-root",
        required=True,
        help="Output directory for artifacts"
    )
    
    parsed = parser.parse_args(args)
    
    try:
        # Load analysis classification data
        with open(parsed.analysis_path, 'r', encoding='utf-8') as f:
            analysis_data = json.load(f)
        
        # Create statement objects from analysis classification output
        raw_statement = Raw_Statement(
            statement_id=analysis_data.get("analysis_classification_id", "raw-001"),
            content={"analysis": analysis_data},
            dossier_evidence_refs=analysis_data.get("dossier_evidence_refs", []),
            metadata={}
        )
        
        handoff_statement = Handoff_Statement(
            statement_id="handoff-001",
            raw_statement_id=raw_statement.statement_id,
            scope="statement_output",
            instructions={"phase": "statement_output", "from_analysis": True},
            metadata={}
        )
        
        llm_statement = LLM_Statement(
            statement_id="llm-001",
            raw_statement_id=raw_statement.statement_id,
            handoff_statement_id=handoff_statement.statement_id,
            advisory_summary=f"Analysis classification completed with {analysis_data.get('classification_count', 0)} classifications",
            interpretations=[{"phase": "statement_output", "status": "completed"}],
            metadata={}
        )
        
        input_data = Statement_Output_Input(
            raw_statement=raw_statement,
            handoff_statement=handoff_statement,
            llm_statement=llm_statement,
            dossier_evidence_refs=analysis_data.get("dossier_evidence_refs", [])
        )
        
        result = run_statement_output(input_data, Path(parsed.output_root))
        print(f"Statement output completed: {parsed.analysis_path}")
        print(f"  Status: {result.status}")
        print(f"  Output: {Path(parsed.output_root) / '04_statement_output.json'}")
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1