"""
Tests for Category-Specific Validation.
"""

import pytest


class TestCategoryValidator:
    """Tests for CategoryValidator class."""
    
    def test_validate_factual_knowledge(self, category_validator):
        """Test factual knowledge validation."""
        valid, errors = category_validator.validate(
            'factual_knowledge',
            'What is the capital of France?',
            'Paris'
        )
        assert valid is True
        assert len(errors) == 0
    
    def test_validate_factual_knowledge_empty(self, category_validator):
        """Test factual knowledge validation with empty answer."""
        valid, errors = category_validator.validate(
            'factual_knowledge',
            'What is the capital of France?',
            ''
        )
        assert valid is False
        assert len(errors) > 0
    
    def test_validate_factual_knowledge_refusal(self, category_validator):
        """Test factual knowledge validation with refusal."""
        valid, errors = category_validator.validate(
            'factual_knowledge',
            'What is the capital of France?',
            'I don\'t know'
        )
        assert valid is False
        assert any('refusal' in e.lower() for e in errors)
    
    def test_validate_mathematical_reasoning(self, category_validator):
        """Test mathematical reasoning validation."""
        valid, errors = category_validator.validate(
            'mathematical_reasoning',
            'Calculate: 15 + 27',
            '42'
        )
        assert valid is True
    
    def test_validate_mathematical_reasoning_non_numeric(self, category_validator):
        """Test mathematical reasoning validation with non-numeric answer."""
        valid, errors = category_validator.validate(
            'mathematical_reasoning',
            'Calculate: 15 + 27',
            'The answer is forty-two'
        )
        assert valid is False
    
    def test_validate_sentiment_classification(self, category_validator):
        """Test sentiment classification validation."""
        valid, errors = category_validator.validate(
            'sentiment_classification',
            'Classify sentiment: I love this!',
            'positive'
        )
        assert valid is True
    
    def test_validate_sentiment_invalid_label(self, category_validator):
        """Test sentiment validation with invalid label."""
        valid, errors = category_validator.validate(
            'sentiment_classification',
            'Classify sentiment: I love this!',
            'happy'
        )
        assert valid is False
    
    def test_validate_sentiment_extra_text(self, category_validator):
        """Test sentiment validation with extra text."""
        valid, errors = category_validator.validate(
            'sentiment_classification',
            'Classify sentiment: I love this!',
            'positive because it is good'
        )
        assert valid is False
    
    def test_validate_text_summarisation(self, category_validator):
        """Test text summarisation validation."""
        valid, errors = category_validator.validate(
            'text_summarisation',
            'Summarize: This is a long text. This is another sentence.',
            'This is a long text.'
        )
        assert valid is True
    
    def test_validate_text_summarisation_copy(self, category_validator):
        """Test text summarisation validation detects copy."""
        source = "This is the source text."
        valid, errors = category_validator.validate(
            'text_summarisation',
            source,
            source
        )
        assert valid is False
        assert any('copy' in e.lower() for e in errors)
    
    def test_validate_named_entity_recognition(self, category_validator):
        """Test NER validation."""
        valid, errors = category_validator.validate(
            'named_entity_recognition',
            'Extract entities: John Doe works at Google.',
            '[{"type": "person", "value": "John Doe"}, {"type": "organization", "value": "Google"}]'
        )
        assert valid is True
    
    def test_validate_named_entity_recognition_invalid_type(self, category_validator):
        """Test NER validation with invalid entity type."""
        valid, errors = category_validator.validate(
            'named_entity_recognition',
            'Extract entities: John Doe',
            '[{"type": "invalid_type", "value": "John Doe"}]'
        )
        assert valid is False
    
    def test_validate_code_debugging(self, category_validator):
        """Test code debugging validation."""
        valid, errors = category_validator.validate(
            'code_debugging',
            'Fix the bug:\ndef add(a, b):\n    return a + b',
            'def add(a, b):\n    return a + b'
        )
        assert valid is True
    
    def test_validate_code_debugging_syntax_error(self, category_validator):
        """Test code debugging validation with syntax error."""
        valid, errors = category_validator.validate(
            'code_debugging',
            'Fix the bug:\ndef add(a, b\n    return a + b',
            'def add(a, b\n    return a + b'
        )
        assert valid is False
    
    def test_validate_logical_reasoning(self, category_validator):
        """Test logical reasoning validation."""
        prompt = "A) Option 1\nB) Option 2\nC) Option 3"
        valid, errors = category_validator.validate(
            'logical_reasoning',
            prompt,
            'B'
        )
        assert valid is True
    
    def test_validate_logical_reasoning_multiple_answers(self, category_validator):
        """Test logical reasoning validation with multiple answers."""
        prompt = "A) Option 1\nB) Option 2\nC) Option 3"
        valid, errors = category_validator.validate(
            'logical_reasoning',
            prompt,
            'A and B'
        )
        assert valid is False
    
    def test_validate_code_generation(self, category_validator):
        """Test code generation validation."""
        valid, errors = category_validator.validate(
            'code_generation',
            'Write a Python function to add two numbers:',
            'def add(a, b):\n    return a + b'
        )
        assert valid is True
    
    def test_validate_code_generation_syntax_error(self, category_validator):
        """Test code generation validation with syntax error."""
        valid, errors = category_validator.validate(
            'code_generation',
            'Write a Python function:',
            'def add(a, b\n    return a + b'
        )
        assert valid is False
    
    def test_validate_code_generation_missing_signature(self, category_validator):
        """Test code generation validation with missing function."""
        valid, errors = category_validator.validate(
            'code_generation',
            'Write a function called my_func:',
            'def other_func():\n    pass'
        )
        assert valid is False
    
    def test_validate_default(self, category_validator):
        """Test default validation for unknown categories."""
        valid, errors = category_validator.validate(
            'unknown_category',
            'Some prompt',
            'Some answer'
        )
        assert valid is True
    
    def test_validate_default_empty(self, category_validator):
        """Test default validation with empty answer."""
        valid, errors = category_validator.validate(
            'unknown_category',
            'Some prompt',
            ''
        )
        assert valid is False
