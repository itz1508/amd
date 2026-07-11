"""
Router

Implements the routing policy for selecting models based on:
1. Deterministic tool availability
2. Category-specific performance
3. Token efficiency
"""

import json
import os
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass
from .model_registry import ModelRegistry, get_model_registry
from .classifier import TaskClassifier, get_classifier
from .local_client import is_local_mode_enabled, get_local_client


@dataclass
class RoutingDecision:
    """Record of a routing decision."""
    task_id: str
    category: str
    selected_model: Optional[str]
    routing_reason: str
    validation_strategy: str
    attempt_count: int
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    latency: Optional[float]
    escalation_reason: Optional[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (for internal logging, not output)."""
        return {
            'task_id': self.task_id,
            'category': self.category,
            'selected_model': self.selected_model,
            'routing_reason': self.routing_reason,
            'validation_strategy': self.validation_strategy,
            'attempt_count': self.attempt_count,
            'input_tokens': self.input_tokens,
            'output_tokens': self.output_tokens,
            'latency': self.latency,
            'escalation_reason': self.escalation_reason
        }


class TaskRouter:
    """Router for task execution."""
    
    def __init__(self, skills_dir: Optional[str] = None):
        """
        Initialize router.
        
        Args:
            skills_dir: Directory containing skill definitions
        """
        self._classifier = get_classifier(skills_dir)
        self._registry = get_model_registry()
        self._skills_dir = skills_dir
        
        # Track routing decisions for logging
        self._decisions: List[RoutingDecision] = []
    
    def initialize_from_env(self) -> bool:
        """Initialize from environment variables."""
        allowed_models = os.environ.get('ALLOWED_MODELS', '')
        return self._registry.initialize(allowed_models)
    
    def _can_use_deterministic_tool(self, category: str, prompt: str) -> Tuple[bool, str, Any]:
        """
        Check if a deterministic tool can fully solve the task.
        
        Args:
            category: The task category
            prompt: The task prompt
            
        Returns:
            Tuple of (can_solve, tool_name, tool_result_or_none)
        """
        # Import tools here to avoid circular imports
        from .tools.json_validator import json_validator
        from .tools.sentiment_validator import sentiment_validator
        from .tools.summary_checker import summary_checker
        from .tools.ner_validator import ner_validator
        from .tools.code_checker import code_checker
        from .tools.logic_checker import logic_checker
        from .arithmetic_detection import extract_arithmetic_expression
        from .tools.arithmetic_evaluator import arithmetic_evaluator
        
        # For mathematical reasoning, try arithmetic evaluator
        if category == 'mathematical_reasoning':
            try:
                expression = extract_arithmetic_expression(prompt)
                if expression:
                    result = arithmetic_evaluator.evaluate_to_string(expression)
                    return True, 'arithmetic_evaluator', result
            except Exception:
                pass
            
            # Try to solve equations
            try:
                if 'solve for' in prompt.lower():
                    result = arithmetic_evaluator.solve_for_variable(prompt)
                    if result is not None:
                        return True, 'arithmetic_evaluator', str(result)
            except Exception:
                pass
        
        # For sentiment classification with clear label in prompt
        if category == 'sentiment_classification':
            # Check if we can extract a label from the prompt itself
            from .tools.sentiment_validator import sentiment_validator
            label = sentiment_validator.extract_label_from_text(prompt)
            if label:
                return True, 'sentiment_validator', label
        
        # For named entity recognition with explicit entities
        if category == 'named_entity_recognition':
            # Check if entities are already marked up in the prompt
            if '[' in prompt and ']' in prompt and '(' in prompt and ')' in prompt:
                # Might be pre-annotated
                pass
        
        # For JSON validation
        if category == 'factual_knowledge':
            # Check if prompt contains JSON that needs validation
            try:
                json_str = json_validator.extract_json_from_text(prompt)
                if json_str:
                    # This is a JSON query, not general factual
                    return True, 'json_validator', json.dumps(json_str)
            except:
                pass
        
        # For logic with explicit candidates
        if category == 'logical_reasoning':
            from .tools.logic_checker import logic_checker
            candidates = logic_checker.extract_candidates(prompt)
            if candidates and len(candidates) == 1:
                return True, 'logic_checker', candidates[0]
        
        return False, '', None
    
    # Categories considered "easy" and safe for local model execution
    LOCAL_SAFE_CATEGORIES = {
        'mathematical_reasoning',
        'sentiment_classification',
        'text_summarisation',
        'factual_knowledge',
        'logical_reasoning',
    }
    
    def _is_local_safe_category(self, category: str) -> bool:
        """Check if a category is safe to run on local model."""
        return category in self.LOCAL_SAFE_CATEGORIES
    
    def _get_local_model_id(self) -> Optional[str]:
        """Get the local model ID if local mode is enabled and available."""
        if not is_local_mode_enabled():
            return None
        local_client = get_local_client()
        if local_client is None or not local_client.is_available():
            return None
        return local_client.model_id
    
    def select_model(self, category: str, 
                    available_models: List[str]) -> Tuple[Optional[str], str]:
        """
        Select the best model for a category from available models.
        
        Routing hierarchy:
        1. Local model for easy/local-safe categories (S1 positive)
        2. Model with best historical performance for category
        3. Model with lowest average tokens for category
        4. First available model (as last resort)
        
        Args:
            category: The task category
            available_models: List of available model IDs
            
        Returns:
            Tuple of (selected_model, reason)
        """
        if not available_models:
            return None, "No models available"
        
        if len(available_models) == 1:
            return available_models[0], "Only one model available"
        
        # S1 positive: prefer local model for easy categories
        local_model_id = self._get_local_model_id()
        if local_model_id is not None and self._is_local_safe_category(category):
            if local_model_id in available_models:
                return local_model_id, f"Local-first: {category} routed to local model"
        
        # Get stats for all models
        model_stats = []
        for model_id in available_models:
            success_rate = self._registry.get_success_rate(model_id, category)
            avg_input, avg_output = self._registry.get_average_tokens(model_id, category)
            total_tokens = (avg_input or 0) + (avg_output or 0)
            model_record = self._registry.get_model(model_id)
            
            model_stats.append({
                'model_id': model_id,
                'success_rate': success_rate if success_rate is not None else 0.0,
                'avg_total_tokens': total_tokens,
                'has_category_history': (
                    model_record is not None
                    and category in model_record.historical_category_results
                )
            })
        
        # Sort by: success rate descending, then tokens ascending
        # Models without category history come last
        def sort_key(stats):
            has_history = 1 if stats['has_category_history'] else 0
            return (-has_history, -stats['success_rate'], stats['avg_total_tokens'])
        
        model_stats.sort(key=sort_key)
        
        # Select the best
        best = model_stats[0]
        
        if best['has_category_history'] and best['success_rate'] > 0:
            reason = f"Best success rate ({best['success_rate']:.2%}) for {category}"
        elif best['has_category_history']:
            reason = f"Best performance history for {category}"
        else:
            reason = "No category history, selected by token efficiency"
        
        return best['model_id'], reason
    
    def route_task(self, task: Dict[str, str]) -> RoutingDecision:
        """
        Route a single task to the appropriate execution path.
        
        Args:
            task: Task dict with task_id and prompt
            
        Returns:
            RoutingDecision with the routing information
        """
        task_id = task['task_id']
        prompt = task['prompt']
        
        # Step 1: Classify
        classification = self._classifier.classify(task_id, prompt)
        category = classification['category']
        
        # Step 2: Check if deterministic tool can solve
        can_solve, tool_name, tool_result = self._can_use_deterministic_tool(category, prompt)
        
        if can_solve:
            return RoutingDecision(
                task_id=task_id,
                category=category,
                selected_model=None,
                routing_reason=f"Deterministic tool {tool_name} can fully solve",
                validation_strategy=f"{tool_name}_validation",
                attempt_count=0,
                input_tokens=None,
                output_tokens=None,
                latency=None,
                escalation_reason=None
            )
        
        # Step 3: Get available models
        available_models = self._registry.get_available_models()
        
        if not available_models:
            return RoutingDecision(
                task_id=task_id,
                category=category,
                selected_model=None,
                routing_reason="No models available",
                validation_strategy="none",
                attempt_count=0,
                input_tokens=None,
                output_tokens=None,
                latency=None,
                escalation_reason="No models available"
            )
        
        # Step 4: Select model based on routing policy
        selected_model, reason = self.select_model(category, available_models)
        
        return RoutingDecision(
            task_id=task_id,
            category=category,
            selected_model=selected_model,
            routing_reason=reason,
            validation_strategy=f"{category}_validation",
            attempt_count=0,
            input_tokens=None,
            output_tokens=None,
            latency=None,
            escalation_reason=None
        )
    
    def route_batch(self, tasks: List[Dict[str, str]]) -> List[RoutingDecision]:
        """
        Route a batch of tasks.
        
        Args:
            tasks: List of task dicts
            
        Returns:
            List of RoutingDecision objects
        """
        decisions = []
        for task in tasks:
            decision = self.route_task(task)
            decisions.append(decision)
        return decisions
    
    def record_decision(self, decision: RoutingDecision) -> None:
        """Record a routing decision for logging."""
        self._decisions.append(decision)
    
    def get_decisions(self) -> List[RoutingDecision]:
        """Get all recorded decisions."""
        return self._decisions
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of routing decisions."""
        summary = {
            'total_decisions': len(self._decisions),
            'by_category': {},
            'by_model': {},
            'deterministic_solves': 0
        }
        
        for decision in self._decisions:
            # Category breakdown
            if decision.category not in summary['by_category']:
                summary['by_category'][decision.category] = 0
            summary['by_category'][decision.category] += 1
            
            # Model breakdown
            if decision.selected_model:
                if decision.selected_model not in summary['by_model']:
                    summary['by_model'][decision.selected_model] = 0
                summary['by_model'][decision.selected_model] += 1
            
            # Deterministic solves
            if decision.selected_model is None and 'tool' in decision.routing_reason:
                summary['deterministic_solves'] += 1
        
        return summary


# Singleton instance
_router_instance = None

def get_router(skills_dir: Optional[str] = None) -> TaskRouter:
    """Get or create the singleton router instance."""
    global _router_instance
    if _router_instance is None:
        _router_instance = TaskRouter(skills_dir)
    return _router_instance
