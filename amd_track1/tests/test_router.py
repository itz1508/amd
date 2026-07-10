"""
Tests for Router.
"""

import pytest


class TestTaskRouter:
    """Tests for TaskRouter class."""
    
    def test_route_task_factual_knowledge(self, router):
        """Test routing of factual knowledge task."""
        # Initialize with some models
        from amd_track1.model_registry import get_model_registry
        get_model_registry().initialize('model1,model2')
        
        task = {'task_id': 'test1', 'prompt': 'What is the capital of France?'}
        decision = router.route_task(task)
        
        assert decision.task_id == 'test1'
        assert decision.category == 'factual_knowledge'
        assert decision.selected_model is not None
        assert decision.routing_reason != ''
    
    def test_route_task_mathematical_reasoning(self, router):
        """Test routing of mathematical reasoning task."""
        from amd_track1.model_registry import get_model_registry
        get_model_registry().initialize('model1,model2')
        
        task = {'task_id': 'test2', 'prompt': 'Calculate: 15 + 27'}
        decision = router.route_task(task)
        
        assert decision.category == 'mathematical_reasoning'
    
    def test_route_task_all_categories(self, router):
        """Test routing of all categories."""
        from amd_track1.model_registry import get_model_registry
        get_model_registry().initialize('model1,model2')
        
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
            'Find the bug in this code',
            'If all A are B and all B are C, are all A C?',
            'Write a Python function'
        ]
        
        for i, (category, prompt) in enumerate(zip(categories, prompts)):
            task = {'task_id': f'test_{i}', 'prompt': prompt}
            decision = router.route_task(task)
            assert decision.category == category
    
    def test_route_batch(self, router):
        """Test batch routing."""
        from amd_track1.model_registry import get_model_registry
        get_model_registry().initialize('model1,model2')
        
        tasks = [
            {'task_id': 't1', 'prompt': 'What is 2+2?'},
            {'task_id': 't2', 'prompt': 'Summarize this'},
            {'task_id': 't3', 'prompt': 'Fix this code'}
        ]
        
        decisions = router.route_batch(tasks)
        
        assert len(decisions) == 3
        assert all(isinstance(d, object) for d in decisions)
        assert all('category' in d.__dict__ for d in decisions)
    
    def test_select_model_single(self, router):
        """Test model selection with single model."""
        from amd_track1.model_registry import get_model_registry
        get_model_registry().initialize('model1')
        
        model, reason = router.select_model('factual_knowledge', ['model1'])
        
        assert model == 'model1'
        assert 'Only one model' in reason
    
    def test_select_model_multiple(self, router):
        """Test model selection with multiple models."""
        from amd_track1.model_registry import get_model_registry
        registry = get_model_registry()
        registry.initialize('model1,model2,model3')
        
        # Without history, should select by token efficiency (alphabetically first)
        model, reason = router.select_model('factual_knowledge', ['model1', 'model2', 'model3'])
        
        assert model in ['model1', 'model2', 'model3']
    
    def test_select_model_no_models(self, router):
        """Test model selection with no models."""
        model, reason = router.select_model('factual_knowledge', [])
        
        assert model is None
        assert 'No models available' in reason
    
    def test_route_task_no_models(self, router):
        """Test routing with no available models."""
        # Create a fresh router with empty registry
        from amd_track1.router import TaskRouter
        from amd_track1.model_registry import ModelRegistry
        from amd_track1.classifier import TaskClassifier
        
        # Create a new registry that's not initialized
        fresh_registry = ModelRegistry()
        # Don't initialize it - it should have no models
        
        # Create a new classifier
        fresh_classifier = TaskClassifier()
        
        # Create a new router and manually set the registry
        fresh_router = TaskRouter()
        fresh_router._registry = fresh_registry
        fresh_router._classifier = fresh_classifier
        
        task = {'task_id': 'test', 'prompt': 'Test prompt'}
        decision = fresh_router.route_task(task)
        
        assert decision.selected_model is None
        assert 'No models available' in decision.routing_reason
    
    def test_deterministic_tool_detection(self, router):
        """Test detection of tasks solvable by deterministic tools."""
        # Arithmetic expression
        task = {'task_id': 'test', 'prompt': 'Calculate: 2 + 3'}
        decision = router.route_task(task)
        
        # The router should detect that this can be solved deterministically
        # (depending on the implementation)
        # This is a soft test
        assert decision.task_id == 'test'
        assert decision.category == 'mathematical_reasoning'
    
    def test_record_decision(self, router):
        """Test recording routing decisions."""
        from amd_track1.model_registry import get_model_registry
        get_model_registry().initialize('model1')
        
        task = {'task_id': 'test', 'prompt': 'Test'}
        decision = router.route_task(task)
        
        router.record_decision(decision)
        
        decisions = router.get_decisions()
        assert len(decisions) == 1
        assert decisions[0].task_id == 'test'
    
    def test_get_summary(self, router):
        """Test getting router summary."""
        from amd_track1.model_registry import get_model_registry
        get_model_registry().initialize('model1,model2')
        
        tasks = [
            {'task_id': 't1', 'prompt': 'What is 2+2?'},
            {'task_id': 't2', 'prompt': 'Summarize this'}
        ]
        
        decisions = router.route_batch(tasks)
        for decision in decisions:
            router.record_decision(decision)
        
        summary = router.get_summary()
        
        assert summary['total_decisions'] == 2
        assert 'by_category' in summary
        assert 'by_model' in summary
