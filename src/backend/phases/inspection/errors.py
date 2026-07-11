"""
Inspection phase errors.
"""


class InspectionError(Exception):
    """Base exception for Inspection phase errors."""
    pass


class InspectionAdmissionError(InspectionError):
    """Input rejected at Inspection admission."""
    pass