"""
Retry and Escalation Policy

Implements bounded retry and escalation for failed tasks.
"""

import time
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from .model_registry import ModelRegistry, get_model_registry


@dataclass
class RetryState:
    """Tracks retry state for a task."""
    task_id: str
    category: str
    attempt_count: int = 0
    last_error: Optional[str] = None
    last_answer: Optional[str] = None
    last_model: Optional[str] = None
    last_validation_errors: List[str] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    
    def can_retry(self, max_attempts: int = 2) -> bool:
        """Check if we can retry this task."""
        return self.attempt_count < max_attempts
    
    def can_escalate(self, max_attempts: int = 2, available_models: int = 1) -> bool:
        """Check if we can escalate to another model."""
        # Can escalate if we have attempts remaining AND there are other models
        return self.attempt_count < max_attempts and available_models > 1
    
    def record_attempt(self, model: Optional[str], answer: Optional[str],
                       validation_errors: Optional[List[str]] = None,
                       error: Optional[str] = None) -> None:
        """Record an attempt."""
        self.attempt_count += 1
        self.last_model = model
        self.last_answer = answer
        self.last_error = error
        if validation_errors:
            self.last_validation_errors = validation_errors
    
    def get_attempt_count(self) -> int:
        """Get current attempt count."""
        return self.attempt_count


class RetryManager:
    """Manages retry and escalation logic."""
    
    MAX_ATTEMPTS = 2  # Default: 2 model attempts per task
    MAX_ATTEMPTS_WITH_JUSTIFICATION = 3  # Can go to 3 with explicit justification
    TIMEOUT_PER_CALL = 300  # 5 minutes per call (below 10-minute limit)
    
    def __init__(self):
        self._registry = get_model_registry()
        self._retry_states: Dict[str, RetryState] = {}
    
    def initialize_task(self, task_id: str, category: str) -> RetryState:
        """
        Initialize retry state for a task.
        
        Args:
            task_id: The task identifier
            category: The task category
            
        Returns:
            RetryState object
        """
        state = RetryState(task_id=task_id, category=category)
        self._retry_states[task_id] = state
        return state
    
    def get_state(self, task_id: str) -> Optional[RetryState]:
        """Get retry state for a task."""
        return self._retry_states.get(task_id)
    
    def should_retry(self, task_id: str, validation_errors: List[str],
                   model_error: Optional[str] = None) -> Tuple[bool, str]:
        """
        Determine if a task should be retried.
        
        Args:
            task_id: The task identifier
            validation_errors: List of validation errors
            model_error: Error from model execution
            
        Returns:
            Tuple of (should_retry, reason)
        """
        state = self.get_state(task_id)
        if not state:
            return False, "No retry state initialized"
        
        # Don't retry deterministic input failures
        if not validation_errors and not model_error:
            return False, "No error to retry"
        
        # Check if we've exceeded attempts
        if not state.can_retry(self.MAX_ATTEMPTS):
            return False, f"Maximum attempts ({self.MAX_ATTEMPTS}) reached"
        
        # Don't retry on provider authentication failures
        if model_error and 'authentication' in model_error.lower():
            return False, "Authentication failure"
        
        # Don't retry on rate limit without changed conditions
        if model_error and 'rate limit' in model_error.lower():
            # Transport retry already happened in executor.py; this is the final decision
            return False, "Rate limit error persisted after transport retry"
        
        # Check if it's a fixable formatting failure
        if validation_errors:
            # These are likely fixable with a retry
            return True, "Validation errors can be fixed"
        
        # Check if it's a capability failure (needs escalation)
        if model_error:
            return True, "Model error, needs escalation"
        
        return False, "Unknown error type"
    
    def should_escalate(self, task_id: str, current_model: str) -> Tuple[bool, Optional[str]]:
        """
        Determine if a task should be escalated to another model.
        
        Args:
            task_id: The task identifier
            current_model: The model that was just used
            
        Returns:
            Tuple of (should_escalate, next_model_or_none)
        """
        state = self.get_state(task_id)
        if not state:
            return False, None
        
        # Don't escalate if we've used max attempts
        if state.attempt_count >= self.MAX_ATTEMPTS:
            # Check if we can justify a third attempt
            available_models = len(self._registry.get_available_models())
            if state.attempt_count < self.MAX_ATTEMPTS_WITH_JUSTIFICATION and available_models > 2:
                # We have room for one more and enough models
                pass
            else:
                return False, None
        
        # Get available models
        available_models = self._registry.get_available_models()
        
        if len(available_models) <= 1:
            return False, None  # No other models to escalate to
        
        # Find a different model
        for model_id in available_models:
            if model_id != current_model:
                return True, model_id
        
        return False, None
    
    def get_next_model(self, task_id: str, current_model: str, category: str) -> Optional[str]:
        """
        Get the next model to try for a task.
        
        Args:
            task_id: The task identifier
            current_model: The current/last model used
            category: The task category
            
        Returns:
            Next model ID or None
        """
        # Try to escalate
        should_escalate, next_model = self.should_escalate(task_id, current_model)
        if should_escalate and next_model:
            return next_model
        
        # No other models available
        return None
    
    def is_fixable_failure(self, validation_errors: List[str]) -> bool:
        """
        Check if validation errors indicate a fixable formatting failure.
        
        Args:
            validation_errors: List of validation errors
            
        Returns:
            True if errors are fixable with retry
        """
        if not validation_errors:
            return False
        
        fixable_patterns = [
            'syntax error',
            'invalid json',
            'empty',
            'format',
            'field',
            'type',
            'parse',
            'missing',
            'exceeds',
            'too many',
            'not a list',
            'not an object'
        ]
        
        for error in validation_errors:
            error_lower = error.lower()
            for pattern in fixable_patterns:
                if pattern in error_lower:
                    return True
        
        return False
    
    def is_capability_failure(self, model_error: Optional[str], 
                               validation_errors: List[str]) -> bool:
        """
        Check if errors indicate a capability failure (needs different model).
        
        Args:
            model_error: Error from model execution
            validation_errors: List of validation errors
            
        Returns:
            True if errors indicate capability mismatch
        """
        # Capability failures include:
        # - Model doesn't understand the task
        # - Model produces consistently wrong answers
        # - Model refuses to answer
        
        if model_error:
            model_error_lower = model_error.lower()
            capability_patterns = [
                'cannot',
                'unable',
                'do not support',
                'not capable',
                'refuse',
                'sorry'
            ]
            for pattern in capability_patterns:
                if pattern in model_error_lower:
                    return True
        
        if validation_errors:
            for error in validation_errors:
                error_lower = error.lower()
                # If it's not fixable, it might be capability
                if 'not one of the valid' in error_lower:
                    return True
        
        return False
    
    def record_attempt(self, task_id: str, model: Optional[str], 
                       answer: Optional[str],
                       validation_errors: Optional[List[str]] = None,
                       error: Optional[str] = None) -> None:
        """
        Record an attempt for a task.
        
        Args:
            task_id: The task identifier
            model: The model that was used
            answer: The answer produced
            validation_errors: List of validation errors
            error: Model execution error
        """
        state = self.get_state(task_id)
        if state:
            state.record_attempt(model, answer, validation_errors, error)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of retry/attempt statistics."""
        summary = {
            'total_tasks': len(self._retry_states),
            'total_attempts': 0,
            'escalations': 0,
            'by_category': {},
            'by_error_type': {}
        }
        
        for state in self._retry_states.values():
            summary['total_attempts'] += state.attempt_count
            
            # Category breakdown
            if state.category not in summary['by_category']:
                summary['by_category'][state.category] = {'attempts': 0, 'errors': {}}
            summary['by_category'][state.category]['attempts'] += state.attempt_count
            
            # Error type breakdown
            if state.last_error:
                error_type = self._classify_error(state.last_error)
                if error_type not in summary['by_error_type']:
                    summary['by_error_type'][error_type] = 0
                summary['by_error_type'][error_type] += 1
        
        return summary
    
    def _classify_error(self, error: str) -> str:
        """Classify an error into a type."""
        error_lower = error.lower()
        
        if 'timeout' in error_lower:
            return 'timeout'
        elif 'authentication' in error_lower or 'auth' in error_lower:
            return 'authentication'
        elif 'rate limit' in error_lower:
            return 'rate_limit'
        elif 'syntax' in error_lower:
            return 'syntax_error'
        elif 'json' in error_lower or 'parse' in error_lower:
            return 'parse_error'
        elif 'validation' in error_lower:
            return 'validation_error'
        else:
            return 'other'


# Singleton instance
_retry_manager_instance = None

def get_retry_manager() -> RetryManager:
    """Get or create the singleton retry manager instance."""
    global _retry_manager_instance
    if _retry_manager_instance is None:
        _retry_manager_instance = RetryManager()
    return _retry_manager_instance
