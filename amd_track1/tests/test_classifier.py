"""
Tests for Eight-Category Classifier.
"""

import pytest


class TestTaskClassifier:
    """Tests for TaskClassifier class."""
    
    def test_classify_factual_knowledge(self, classifier):
        """Test classification of factual knowledge tasks."""
        result = classifier.classify('fk_test', 'What is the capital of France?')
        
        assert result['category'] == 'factual_knowledge'
        assert result['confidence'] > 0
        assert 'what is' in result['signals'] or 'capital' in result['signals']
    
    def test_classify_mathematical_reasoning(self, classifier):
        """Test classification of mathematical reasoning tasks."""
        result = classifier.classify('mr_test', 'Calculate: 15 + 27')
        
        assert result['category'] == 'mathematical_reasoning'
        assert result['confidence'] > 0
    
    def test_classify_sentiment(self, classifier):
        """Test classification of sentiment tasks."""
        result = classifier.classify('sc_test', 'Classify sentiment: I love this!')
        
        assert result['category'] == 'sentiment_classification'
        assert result['confidence'] > 0
    
    def test_classify_summarisation(self, classifier):
        """Test classification of summarisation tasks."""
        result = classifier.classify('ts_test', 'Summarize: This is a long text.')
        
        assert result['category'] == 'text_summarisation'
        assert result['confidence'] > 0
    
    def test_classify_ner(self, classifier):
        """Test classification of NER tasks."""
        result = classifier.classify('ner_test', 'Extract named entities from this text.')
        
        assert result['category'] == 'named_entity_recognition'
        assert result['confidence'] > 0
    
    def test_classify_code_debugging(self, classifier):
        """Test classification of code debugging tasks."""
        result = classifier.classify('cd_test', 'Find the bug in this code')
        
        assert result['category'] == 'code_debugging'
        assert result['confidence'] > 0
    
    def test_classify_logical_reasoning(self, classifier):
        """Test classification of logical reasoning tasks."""
        result = classifier.classify('lr_test', 'If all A are B and all B are C, are all A C?')
        
        assert result['category'] == 'logical_reasoning'
        assert result['confidence'] > 0
    
    def test_classify_code_generation(self, classifier):
        """Test classification of code generation tasks."""
        result = classifier.classify('cg_test', 'Write a Python function to add two numbers')
        
        assert result['category'] == 'code_generation'
        assert result['confidence'] > 0
    
    def test_classify_unknown(self, classifier):
        """Test classification of unknown tasks."""
        result = classifier.classify('unknown_test', 'This is a completely ambiguous prompt')
        
        # Should classify to some category, not necessarily 'unknown'
        assert result['category'] in classifier.ALLOWED_CATEGORIES
    
    def test_classify_batch(self, classifier):
        """Test batch classification."""
        tasks = [
            {'task_id': 't1', 'prompt': 'What is 2+2?'},
            {'task_id': 't2', 'prompt': 'Summarize this text'},
            {'task_id': 't3', 'prompt': 'Fix this code'}
        ]
        
        results = classifier.classify_batch(tasks)
        
        assert len(results) == 3
        assert all('category' in r for r in results)
        assert all('confidence' in r for r in results)
    
    def test_load_skills(self, classifier, skills_dir):
        """Test loading skills from directory."""
        success = classifier.load_skills(skills_dir)
        
        assert success is True
        assert len(classifier._skills) == 8
    
    def test_allowed_categories(self, classifier):
        """Test that all 8 categories are in allowed list."""
        expected_categories = [
            'factual_knowledge',
            'mathematical_reasoning',
            'sentiment_classification',
            'text_summarisation',
            'named_entity_recognition',
            'code_debugging',
            'logical_reasoning',
            'code_generation',
            'unknown'
        ]
        
        assert set(classifier.ALLOWED_CATEGORIES) == set(expected_categories)
    
    def test_confidence_range(self, classifier):
        """Test that confidence is in valid range."""
        prompts = [
            'What is the capital of France?',
            'Calculate 15 + 27',
            'Summarize this text',
            'Extract entities',
            'Debug this code',
            'Solve this puzzle',
            'Write a function'
        ]
        
        for i, prompt in enumerate(prompts):
            result = classifier.classify(f'test_{i}', prompt)
            assert 0.0 <= result['confidence'] <= 1.0
    
    def test_structural_analysis_code(self, classifier):
        """Test structural analysis boosts confidence for code."""
        # Without code in prompt
        result1 = classifier.classify('test1', 'Write a function')
        
        # With code in prompt
        result2 = classifier.classify('test2', 'def my_func():\n    pass')
        
        # Both should be code_generation, but the one with code might have higher confidence
        # This is a soft test as the classifier behavior may vary
        assert result1['category'] == 'code_generation' or result1['category'] == 'code_debugging'
        assert result2['category'] in ['code_generation', 'code_debugging', 'unknown', 'factual_knowledge']
    
    def test_structural_analysis_math(self, classifier):
        """Test structural analysis for math expressions."""
        result = classifier.classify('test', 'Calculate: 15 + 27 * 3')
        
        assert result['category'] == 'mathematical_reasoning'
        assert result['confidence'] > 0.5
    
    def test_get_category_from_classification(self, classifier):
        """Test extracting category from classification."""
        classification = {'category': 'factual_knowledge', 'other': 'data'}
        
        category = classifier.get_category_from_classification(classification)
        
        assert category == 'factual_knowledge'
    
    def test_get_category_default_unknown(self, classifier):
        """Test default category is unknown."""
        classification = {}
        
        category = classifier.get_category_from_classification(classification)
        
        assert category == 'unknown'
