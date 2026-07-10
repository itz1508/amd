"""
Tests for Prompt Construction.
"""

import pytest


class TestPromptBuilder:
    """Tests for PromptBuilder class."""
    
    def test_build_prompt_factual_knowledge(self, prompt_builder):
        """Test building factual knowledge prompt."""
        result = prompt_builder.build_prompt(
            'test1',
            'What is the capital of France?',
            'factual_knowledge'
        )
        
        assert result['category'] == 'factual_knowledge'
        assert 'What is the capital of France?' in result['prompt']
        assert result['output_shape'] != ''
    
    def test_build_prompt_mathematical_reasoning(self, prompt_builder):
        """Test building mathematical reasoning prompt."""
        result = prompt_builder.build_prompt(
            'test2',
            'Calculate: 15 + 27',
            'mathematical_reasoning'
        )
        
        assert result['category'] == 'mathematical_reasoning'
        assert 'Calculate: 15 + 27' in result['prompt']
    
    def test_build_prompt_sentiment(self, prompt_builder):
        """Test building sentiment prompt."""
        result = prompt_builder.build_prompt(
            'test3',
            'Classify sentiment: I love this!',
            'sentiment_classification'
        )
        
        assert result['category'] == 'sentiment_classification'
        assert 'positive' in result['prompt'].lower() or 'negative' in result['prompt'].lower() or 'neutral' in result['prompt'].lower()
    
    def test_build_prompt_all_categories(self, prompt_builder):
        """Test building prompts for all categories."""
        categories = [
            'factual_knowledge',
            'mathematical_reasoning',
            'sentiment_classification',
            'text_summarisation',
            'named_entity_recognition',
            'code_debugging',
            'logical_reasoning',
            'code_generation'
        ]
        
        prompts = [
            'What is the capital of France?',
            'Calculate: 15 + 27',
            'Classify sentiment: I love this!',
            'Summarize: This is a long text.',
            'Extract named entities from this text.',
            'Fix the bug in this code',
            'Solve this logic puzzle',
            'Write a Python function'
        ]
        
        for category, prompt in zip(categories, prompts):
            result = prompt_builder.build_prompt('test', prompt, category)
            assert result['category'] == category
            assert prompt in result['prompt']
    
    def test_build_prompt_auto_classify(self, prompt_builder):
        """Test building prompt with auto-classification."""
        result = prompt_builder.build_prompt(
            'test',
            'What is the capital of France?',
            None  # Let it auto-classify
        )
        
        assert result['category'] == 'factual_knowledge'
    
    def test_build_batch_prompts(self, prompt_builder):
        """Test building batch of prompts."""
        tasks = [
            {'task_id': 't1', 'prompt': 'What is 2+2?'},
            {'task_id': 't2', 'prompt': 'Summarize this text'},
            {'task_id': 't3', 'prompt': 'Fix this code'}
        ]
        
        results = prompt_builder.build_batch_prompts(tasks)
        
        assert len(results) == 3
        assert all('category' in r for r in results)
        assert all('prompt' in r for r in results)
    
    def test_get_category_instructions(self, prompt_builder):
        """Test getting category-specific instructions."""
        instructions = prompt_builder._get_category_instructions('factual_knowledge')
        assert 'directly' in instructions.lower() or 'concise' in instructions.lower()
        
        instructions = prompt_builder._get_category_instructions('mathematical_reasoning')
        assert 'numeric' in instructions.lower() or 'final' in instructions.lower()
        
        instructions = prompt_builder._get_category_instructions('sentiment_classification')
        assert 'positive' in instructions.lower() or 'negative' in instructions.lower()
    
    def test_prompt_templates_exist(self, prompt_builder):
        """Test that all category templates exist."""
        categories = [
            'factual_knowledge',
            'mathematical_reasoning',
            'sentiment_classification',
            'text_summarisation',
            'named_entity_recognition',
            'code_debugging',
            'logical_reasoning',
            'code_generation'
        ]
        
        for category in categories:
            assert category in prompt_builder.PROMPT_TEMPLATES
            assert 'base' in prompt_builder.PROMPT_TEMPLATES[category]
    
    def test_output_shapes_exist(self, prompt_builder):
        """Test that all category output shapes exist."""
        categories = [
            'factual_knowledge',
            'mathematical_reasoning',
            'sentiment_classification',
            'text_summarisation',
            'named_entity_recognition',
            'code_debugging',
            'logical_reasoning',
            'code_generation'
        ]
        
        for category in categories:
            assert category in prompt_builder.OUTPUT_SHAPES
    
    def test_extract_parameters_word_limit(self, prompt_builder):
        """Test parameter extraction for word limit."""
        params = prompt_builder._extract_parameters(
            'Summarize in 10 words or less: some text',
            'text_summarisation'
        )
        
        assert 'limit' in params
        assert params['limit'] == '10'
    
    def test_extract_parameters_sentence_limit(self, prompt_builder):
        """Test parameter extraction for sentence limit."""
        params = prompt_builder._extract_parameters(
            'Summarize in 5 sentences or less: some text',
            'text_summarisation'
        )
        
        assert 'limit' in params
        assert params['limit'] == '5'
    
    def test_select_template_variant(self, prompt_builder):
        """Test template variant selection."""
        variant = prompt_builder._select_template_variant('factual_knowledge', 'test')
        assert variant == 'direct'

    def test_build_prompt_uses_skill_default_template(self, prompt_builder):
        """Test that loaded skill JSON controls default prompt template."""
        result = prompt_builder.build_prompt(
            'test',
            'What is the capital of France?',
            'factual_knowledge'
        )

        assert result['prompt'] == 'What is the capital of France?'
        assert result['output_shape'] == 'string'
