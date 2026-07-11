"""Request-kind classification tests for Analysis_Classification phase."""
from backend.phases.analysis_classification import run_analysis_classification
from backend.phases.analysis_classification.classifier import classify_request_kind
from tests.case_builder.analysis_classification_case_builder import Analysis_ClassificationInputBuilder


class TestRequestClassification:
    """Analysis_Classification must classify the request kind from request_text."""

    def test_corrective_request_kind(self, tmp_path):
        inp = Analysis_ClassificationInputBuilder().with_request_text("Fix the bug in module.py").build()
        result = run_analysis_classification(inp, tmp_path)
        assert result.request_kind == "corrective"

    def test_additive_request_kind(self, tmp_path):
        inp = Analysis_ClassificationInputBuilder().with_request_text("Add a new feature to handle retries").build()
        result = run_analysis_classification(inp, tmp_path)
        assert result.request_kind == "additive"

    def test_migration_request_kind(self, tmp_path):
        inp = Analysis_ClassificationInputBuilder().with_request_text("Migrate the service to the new API").build()
        result = run_analysis_classification(inp, tmp_path)
        assert result.request_kind == "migration"

    def test_diagnostic_request_kind(self, tmp_path):
        inp = Analysis_ClassificationInputBuilder().with_request_text("Diagnose why the tests are failing").build()
        result = run_analysis_classification(inp, tmp_path)
        assert result.request_kind == "diagnostic"

    def test_verification_request_kind(self, tmp_path):
        inp = Analysis_ClassificationInputBuilder().with_request_text("Verify that the fix passes all tests").build()
        result = run_analysis_classification(inp, tmp_path)
        assert result.request_kind == "verification"

    def test_informational_request_kind(self, tmp_path):
        inp = Analysis_ClassificationInputBuilder().with_request_text("Summarize the repository structure").build()
        result = run_analysis_classification(inp, tmp_path)
        assert result.request_kind == "informational"

    def test_unknown_request_kind(self, tmp_path):
        inp = Analysis_ClassificationInputBuilder().with_request_text("lorem ipsum dolor sit amet").build()
        result = run_analysis_classification(inp, tmp_path)
        assert result.request_kind == "unknown"

    def test_classifier_function_directly(self):
        assert classify_request_kind("Fix the crash") == "corrective"
        assert classify_request_kind("Add logging") == "additive"
        assert classify_request_kind("Migrate to pydantic v2") == "migration"
        assert classify_request_kind("Explain this function") == "diagnostic"
        assert classify_request_kind("Validate inputs") == "verification"
        assert classify_request_kind("Document the API") == "informational"
        assert classify_request_kind("something else") == "unknown"