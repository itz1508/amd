"""Statement Output errors."""
class StatementOutputError(Exception):
    """Base error for Statement Output phase."""
    pass


class MissingRawStatementError(StatementOutputError):
    """Raised when raw_statement_id is missing."""
    pass


class MissingHandoffStatementError(StatementOutputError):
    """Raised when handoff_statement_id is missing."""
    pass


class MismatchedRawStatementError(StatementOutputError):
    """Raised when llm raw_statement_id does not match handoff raw_statement_id."""
    pass


class MismatchedHandoffStatementError(StatementOutputError):
    """Raised when llm handoff_statement_id does not match handoff statement_id."""
    pass


class SequenceValidationError(StatementOutputError):
    """Raised when sequence order is violated."""
    pass