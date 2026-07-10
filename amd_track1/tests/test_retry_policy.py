"""
Tests for Retry and Escalation Policy.
"""

import pytest
import time


class TestRetryState:
    """Tests for RetryState dataclass."""
    
    def test_can_retry(self):
        """Test can_retry method."""
        from amd_track1.retry_policy import RetryState
        
        state = RetryState('test', 'factual_knowledge', attempt_count=0)
        assert state.can_retry() is True
        
        state = RetryState('test', 'factual_knowledge', attempt_count=2)
        assert state.can_retry() is False
    
    def test_can_escalate(self):
        """Test can_escalate method."""
        from amd_track1.retry_policy import RetryState
        
        state = RetryState('test', 'factual_knowledge', attempt_count=0)
        assert state.can_escalate(available_models=2) is True
        
        state = RetryState('test', 'factual_knowledge', attempt_count=2)
        assert state.can_escalate(available_models=2) is False
    
    def test_record_attempt(self):
        """Test record_attempt method."""
        from amd_track1.retry_policy import RetryState
        
        state = RetryState('test', 'factual_knowledge')
        initial_count = state.get_attempt_count()
        
        state.record_attempt('model1', 'answer', ['error1'], 'model error')
        
        assert state.get_attempt_count() == initial_count + 1
        assert state.last_model == 'model1'
        assert state.last_answer == 'answer'
        assert state.last_error == 'model error'
    
    def test_get_attempt_count(self):
        """Test get_attempt_count method."""
        from amd_track1.retry_policy import RetryState
        
        state = RetryState('test', 'factual_knowledge', attempt_count=3)
        assert state.get_attempt_count() == 3


class TestRetryManager:
    """Tests for RetryManager class."""
    
    def test_initialize_task(self, retry_manager):
        """Test task initialization."""
        state = retry_manager.initialize_task('test1', 'factual_knowledge')
        
        assert state.task_id == 'test1'
        assert state.category == 'factual_knowledge'
        assert state.attempt_count == 0
    
    def test_get_state(self, retry_manager):
        """Test getting task state."""
        retry_manager.initialize_task('test1', 'factual_knowledge')
        
        state = retry_manager.get_state('test1')
        assert state is not None
        assert state.task_id == 'test1'
        
        state = retry_manager.get_state('unknown')
        assert state is None
    
    def test_should_retry_validation_errors(self, retry_manager):
        """Test retry on validation errors."""
        retry_manager.initialize_task('test1', 'factual_knowledge')
        
        should_retry, reason = retry_manager.should_retry(
            'test1',
            ['Syntax error in output'],
            None
        )
        
        assert should_retry is True
    
    def test_should_not_retry_max_attempts(self, retry_manager):
        """Test not retrying on max attempts."""
        state = retry_manager.initialize_task('test1', 'factual_knowledge')
        state.record_attempt('model1', 'answer', [], None)
        state.record_attempt('model1', 'answer', [], None)
        
        should_retry, reason = retry_manager.should_retry(
            'test1',
            ['Error'],
            None
        )
        
        assert should_retry is False
        assert 'Maximum attempts' in reason
    
    def test_should_not_retry_authentication(self, retry_manager):
        """Test not retrying on authentication error."""
        retry_manager.initialize_task('test1', 'factual_knowledge')
        
        should_retry, reason = retry_manager.should_retry(
            'test1',
            [],
            'Authentication failed'
        )
        
        assert should_retry is False
        assert 'Authentication' in reason
    
    def test_should_not_retry_rate_limit(self, retry_manager):
        """Test not retrying on rate limit."""
        retry_manager.initialize_task('test1', 'factual_knowledge')
        
        should_retry, reason = retry_manager.should_retry(
            'test1',
            [],
            'Rate limit exceeded'
        )
        
        assert should_retry is False
        assert 'Rate limit' in reason
    
    def test_should_escalate(self, retry_manager):
        """Test escalation to another model."""
        from amd_track1.model_registry import get_model_registry
        registry = get_model_registry()
        registry._initialized = False
        registry._models.clear()
        registry.initialize('model1,model2,model3')
        
        retry_manager.initialize_task('test1', 'factual_knowledge')
        retry_manager.record_attempt('test1', 'model1', 'answer', [], None)
        
        should_escalate, next_model = retry_manager.should_escalate('test1', 'model1')
        
        assert should_escalate is True
        assert next_model in ['model2', 'model3']
    
    def test_get_next_model(self, retry_manager):
        """Test getting next model."""
        from amd_track1.model_registry import get_model_registry
        registry = get_model_registry()
        registry._initialized = False
        registry._models.clear()
        registry.initialize('model1,model2')
        
        retry_manager.initialize_task('test1', 'factual_knowledge')
        
        next_model = retry_manager.get_next_model('test1', 'model1', 'factual_knowledge')
        
        assert next_model == 'model2'
    
    def test_get_next_model_no_more(self, retry_manager):
        """Test getting next model when none available."""
        from amd_track1.retry_policy import RetryManager
        from amd_track1.model_registry import ModelRegistry
        
        # Create a fresh retry manager with a fresh registry
        fresh_retry = RetryManager()
        fresh_registry = ModelRegistry()
        fresh_registry.initialize('model1')
        
        # Manually set the registry
        fresh_retry._registry = fresh_registry
        
        fresh_retry.initialize_task('test1', 'factual_knowledge')
        
        next_model = fresh_retry.get_next_model('test1', 'model1', 'factual_knowledge')
        
        assert next_model is None
    
    def test_is_fixable_failure(self, retry_manager):
        """Test fixable failure detection."""
        assert retry_manager.is_fixable_failure(['Syntax error']) is True
        assert retry_manager.is_fixable_failure(['Invalid JSON']) is True
        assert retry_manager.is_fixable_failure(['Missing field']) is True
        assert retry_manager.is_fixable_failure(['Some other error']) is False
    
    def test_is_capability_failure(self, retry_manager):
        """Test capability failure detection."""
        assert retry_manager.is_capability_failure('Model cannot handle this task', []) is True
        assert retry_manager.is_capability_failure('Sorry, I cannot', []) is True
        assert retry_manager.is_capability_failure(None, ['Not one of the valid choices']) is True
        assert retry_manager.is_capability_failure(None, ['Syntax error']) is False
    
    def test_record_attempt(self, retry_manager):
        """Test recording attempt."""
        retry_manager.initialize_task('test1', 'factual_knowledge')
        retry_manager.record_attempt('test1', 'model1', 'answer', ['error'], 'model error')
        
        state = retry_manager.get_state('test1')
        assert state.attempt_count == 1
        assert state.last_model == 'model1'
    
    def test_get_summary(self, retry_manager):
        """Test getting summary."""
        retry_manager.initialize_task('test1', 'factual_knowledge')
        retry_manager.initialize_task('test2', 'mathematical_reasoning')
        
        retry_manager.record_attempt('test1', 'model1', 'answer1', ['error1'], 'Error 1')
        retry_manager.record_attempt('test2', 'model2', 'answer2', [], None)
        
        summary = retry_manager.get_summary()
        
        assert summary['total_tasks'] == 2
        assert summary['total_attempts'] == 2
        assert 'factual_knowledge' in summary['by_category']
        assert 'mathematical_reasoning' in summary['by_category']


class TestRetryManagerClassifyError:
    """Tests for error classification in RetryManager."""
    
    def test_classify_timeout(self, retry_manager):
        """Test timeout error classification."""
        assert retry_manager._classify_error('Timeout error') == 'timeout'
    
    def test_classify_authentication(self, retry_manager):
        """Test authentication error classification."""
        assert retry_manager._classify_error('Authentication failed') == 'authentication'
        assert retry_manager._classify_error('Auth error') == 'authentication'
    
    def test_classify_rate_limit(self, retry_manager):
        """Test rate limit error classification."""
        assert retry_manager._classify_error('Rate limit exceeded') == 'rate_limit'
    
    def test_classify_syntax_error(self, retry_manager):
        """Test syntax error classification."""
        assert retry_manager._classify_error('Syntax error in code') == 'syntax_error'
    
    def test_classify_parse_error(self, retry_manager):
        """Test parse error classification."""
        assert retry_manager._classify_error('JSON parse error') == 'parse_error'
    
    def test_classify_unknown(self, retry_manager):
        """Test unknown error classification."""
        assert retry_manager._classify_error('Some unknown error') == 'other'
