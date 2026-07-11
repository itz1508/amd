"""Statement Output schema definitions."""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Raw_Statement:
    """Normalized statement content with dossier evidence references.
    
    Statement_id is the stable identifier.
    Contains dossier evidence references provided by backend.dossier.
    """
    statement_id: str
    content: dict[str, Any]
    dossier_evidence_refs: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "statement_id": self.statement_id,
            "content": self.content,
            "dossier_evidence_refs": list(self.dossier_evidence_refs),
            "metadata": dict(self.metadata),
        }


@dataclass
class Handoff_Statement:
    """Handoff statement referencing Raw_Statement.
    
    statement_id is the stable identifier.
    raw_statement_id must equal Raw_Statement.statement_id.
    Contains scope and bounded instructions.
    """
    statement_id: str
    raw_statement_id: str
    scope: str
    instructions: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "statement_id": self.statement_id,
            "raw_statement_id": self.raw_statement_id,
            "scope": self.scope,
            "instructions": dict(self.instructions),
            "metadata": dict(self.metadata),
        }


@dataclass
class LLM_Statement:
    """LLM advisory statement.
    
    NOT execution authority.
    Must reference both raw_statement_id and handoff_statement_id.
    raw_statement_id must equal Raw_Statement.statement_id.
    handoff_statement_id must equal Handoff_Statement.statement_id.
    """
    statement_id: str
    raw_statement_id: str
    handoff_statement_id: str
    advisory_summary: str
    interpretations: list[dict[str, Any]]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "statement_id": self.statement_id,
            "raw_statement_id": self.raw_statement_id,
            "handoff_statement_id": self.handoff_statement_id,
            "advisory_summary": self.advisory_summary,
            "interpretations": list(self.interpretations),
            "metadata": dict(self.metadata),
            "is_advisory": True,
        }


@dataclass
class Statement_Output_Input:
    """Input boundary for Statement_Output phase.
    
    Typed fixture representing future Analysis_Classification output.
    Contains the strict chain: Raw -> Handoff -> LLM.
    Dossier evidence references are preserved through backend.dossier.
    """
    raw_statement: Raw_Statement
    handoff_statement: Handoff_Statement
    llm_statement: LLM_Statement
    dossier_evidence_refs: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_statement": self.raw_statement.to_dict(),
            "handoff_statement": self.handoff_statement.to_dict(),
            "llm_statement": self.llm_statement.to_dict(),
            "dossier_evidence_refs": list(self.dossier_evidence_refs),
        }


@dataclass
class Statement_Output_Output:
    """Final Statement_Output artifact.
    
    Preserves dossier evidence references.
    Does not grant execution authority.
    """
    phase: str
    status: str
    statement_output_id: str
    raw_statement_id: str
    handoff_statement_id: str
    llm_statement_id: str
    dossier_evidence_refs: list[str]
    statement_output_fingerprint: str
    output_content: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "status": self.status,
            "statement_output_id": self.statement_output_id,
            "raw_statement_id": self.raw_statement_id,
            "handoff_statement_id": self.handoff_statement_id,
            "llm_statement_id": self.llm_statement_id,
            "dossier_evidence_refs": list(self.dossier_evidence_refs),
            "statement_output_fingerprint": self.statement_output_fingerprint,
            "output_content": dict(self.output_content),
            "metadata": dict(self.metadata),
        }
