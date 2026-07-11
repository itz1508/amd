"""Statement Output validator."""
from .schema import Raw_Statement, Handoff_Statement, LLM_Statement
from .errors import (
    MissingRawStatementError,
    MissingHandoffStatementError,
    MismatchedRawStatementError,
    MismatchedHandoffStatementError,
)


def validate_raw_handoff_llm_sequence(
    raw: Raw_Statement,
    handoff: Handoff_Statement,
    llm: LLM_Statement,
) -> None:
    """Validate strict Raw -> Handoff -> LLM sequence.
    
    Rules:
    - Handoff.raw_statement_id must equal Raw.statement_id
    - LLM.raw_statement_id must equal Raw.statement_id
    - LLM.handoff_statement_id must equal Handoff.handoff_statement_id
    
    Raises:
        MissingRawStatementError: if raw reference missing or mismatched
        MissingHandoffStatementError: if handoff reference missing
        MismatchedRawStatementError: if llm raw_statement_id != handoff raw_statement_id
        MismatchedHandoffStatementError: if llm handoff_statement_id != handoff.handoff_statement_id
    """
    if not handoff.raw_statement_id:
        raise MissingRawStatementError(
            f"handoff_statement.raw_statement_id is empty; "
            f"expected {raw.statement_id}"
        )
    if handoff.raw_statement_id != raw.statement_id:
        raise MismatchedRawStatementError(
            f"handoff_statement.raw_statement_id={handoff.raw_statement_id} "
            f"does not match raw.statement_id={raw.statement_id}"
        )

    if not llm.raw_statement_id:
        raise MissingRawStatementError(
            f"llm_statement.raw_statement_id is empty; "
            f"expected {raw.statement_id}"
        )
    if llm.raw_statement_id != raw.statement_id:
        raise MismatchedRawStatementError(
            f"llm_statement.raw_statement_id={llm.raw_statement_id} "
            f"does not match raw.statement_id={raw.statement_id}"
        )

    if not llm.handoff_statement_id:
        raise MissingHandoffStatementError(
            f"llm_statement.handoff_statement_id is empty; "
            f"expected {handoff.statement_id}"
        )
    if llm.handoff_statement_id != handoff.statement_id:
        raise MismatchedHandoffStatementError(
            f"llm_statement.handoff_statement_id={llm.handoff_statement_id} "
            f"does not match handoff_statement.statement_id={handoff.statement_id}"
        )
