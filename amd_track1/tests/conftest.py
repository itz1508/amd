"""
Pytest configuration and fixtures for AMD Track 1 tests.
"""

import os
import pytest
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def skills_dir():
    """Path to skills directory."""
    return os.path.join(os.path.dirname(__file__), '..', 'skills')


@pytest.fixture
def benchmarks_dir():
    """Path to benchmarks directory."""
    return os.path.join(os.path.dirname(__file__), '..', 'benchmarks')


@pytest.fixture
def input_validation():
    """InputValidator instance."""
    from amd_track1.input_validation import InputValidator
    return InputValidator()


@pytest.fixture
def classifier(skills_dir):
    """TaskClassifier instance with skills loaded."""
    from amd_track1.classifier import TaskClassifier
    classifier = TaskClassifier(skills_dir)
    classifier.load_skills(skills_dir)
    return classifier


@pytest.fixture
def model_registry():
    """ModelRegistry instance."""
    from amd_track1.model_registry import ModelRegistry
    registry = ModelRegistry()
    # Initialize with dummy models for testing
    registry.initialize('model1,model2,model3')
    return registry


@pytest.fixture
def router(skills_dir):
    """TaskRouter instance."""
    from amd_track1.router import TaskRouter
    return TaskRouter(skills_dir)


@pytest.fixture
def prompt_builder(skills_dir):
    """PromptBuilder instance."""
    from amd_track1.prompt_builder import PromptBuilder
    return PromptBuilder(skills_dir)


@pytest.fixture
def category_validator():
    """CategoryValidator instance."""
    from amd_track1.category_validator import CategoryValidator
    return CategoryValidator()


@pytest.fixture
def retry_manager():
    """RetryManager instance."""
    from amd_track1.retry_policy import RetryManager
    return RetryManager()


# Fixtures for tools
@pytest.fixture
def arithmetic_evaluator():
    """ArithmeticEvaluator instance."""
    from amd_track1.tools.arithmetic_evaluator import ArithmeticEvaluator
    return ArithmeticEvaluator()


@pytest.fixture
def json_validator():
    """JSONValidator instance."""
    from amd_track1.tools.json_validator import JSONValidator
    return JSONValidator()


@pytest.fixture
def sentiment_validator():
    """SentimentValidator instance."""
    from amd_track1.tools.sentiment_validator import SentimentValidator
    return SentimentValidator()


@pytest.fixture
def summary_checker():
    """SummaryConstraintChecker instance."""
    from amd_track1.tools.summary_checker import SummaryConstraintChecker
    return SummaryConstraintChecker()


@pytest.fixture
def ner_validator():
    """NamedEntityValidator instance."""
    from amd_track1.tools.ner_validator import NamedEntityValidator
    return NamedEntityValidator()


@pytest.fixture
def code_checker():
    """CodeSyntaxChecker instance."""
    from amd_track1.tools.code_checker import CodeSyntaxChecker
    return CodeSyntaxChecker()


@pytest.fixture
def logic_checker():
    """LogicConsistencyChecker instance."""
    from amd_track1.tools.logic_checker import LogicConsistencyChecker
    return LogicConsistencyChecker()


@pytest.fixture
def submission_validator():
    """SubmissionValidator instance."""
    from amd_track1.tools.submission_validator import SubmissionValidator
    return SubmissionValidator()
