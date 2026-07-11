"""
Analysis_Classification error types.
"""


class Analysis_Classification_Error(Exception):
    """Base error for Analysis_Classification phase."""
    pass


class Analysis_Classification_Admission_Error(Analysis_Classification_Error):
    """Raised when the input fails structural admission validation."""
    pass