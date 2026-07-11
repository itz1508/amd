"""
Analysis_Classification phase.

Consumes a completed Scan_Output and the original request context.
Produces evidence-backed classifications for every detected source record.
"""

from backend.phases.analysis_classification.schema import (
    Analysis_Classification_Input,
    Analysis_Classification_Output,
    Analysis_Item,
    Classification_Decision,
    Classification_Evidence,
    Classification_Group,
    Classification_Notice,
)
from backend.phases.analysis_classification.errors import (
    Analysis_Classification_Error,
    Analysis_Classification_Admission_Error,
)
from backend.phases.analysis_classification.runner import run_analysis_classification

__all__ = [
    "Analysis_Classification_Input",
    "Analysis_Classification_Output",
    "Analysis_Item",
    "Classification_Decision",
    "Classification_Evidence",
    "Classification_Group",
    "Classification_Notice",
    "Analysis_Classification_Error",
    "Analysis_Classification_Admission_Error",
    "run_analysis_classification",
]