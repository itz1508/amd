"""
Router

Implements the routing policy for selecting models based on:
1. Deterministic tool availability
2. Category-specific performance
3. Token efficiency

FIX: This submission build routes ONLY to deterministic tools or Fireworks.
Local inference has been removed from the routing path entirely (not just
gated behind an env var check) — there is no code path in this file that can
select a local model, regardless of what environment variables are set.
"""

import json
import os
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass
from .model_registry import ModelRegistry, get_model_registry
from .classifier import TaskClassifier, get_classifier


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
    """Router for task execution. Fireworks-only: no local inference path exists."""

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
        This is pure computation (regex/parsing), not model inference of any
        kind — it does not count as "local inference" under the hackathon
        rules and is safe to use freely.

        Args:
            category: The task category
            prompt: The task prompt

        Returns:
            Tuple of (can_solve, tool_name, tool_result_or_none)
        """
        from .tools import (
            ArithmeticEvaluator,
            json_validator,
            sentiment_validator,
            summary_checker,
            ner_validator,
            code_checker,
            logic_checker
        )

        if category == 'mathematical_reasoning':
            try:
                import re
                matches = re.findall(r'[\d]+[\s]*[+\-*/%^**][\s]*[\d]+', prompt)
                matches += re.findall(r'\([\d]+[\s]*[+\-*/%^**][\s]*[\d]+\)', prompt)

                if matches:
                    result = ArithmeticEvaluator().evaluate_to_string(matches[0])
                    return True, 'arithmetic_evaluator', result
            except Exception:
                pass

            try:
                if 'solve for' in prompt.lower():
                    result = ArithmeticEvaluator().solve_for_variable(prompt)
                    if result is not None:
                        return True, 'arithmetic_evaluator', str(result)
            except Exception:
                pass

        if category == 'sentiment_classification':
            from .tools.sentiment_validator import sentiment_validator
            label = sentiment_validator.extract_label_from_text(prompt)
            if label:
                return True, 'sentiment_validator', label

        if category == 'factual_knowledge':
            try:
                json_str = json_validator.extract_json_from_text(prompt)
                if json_str:
                    return True, 'json_validator', json.dumps(json_str)
            except Exception:
                pass

        if category == 'logical_reasoning':
            from .tools.logic_checker import logic_checker
            candidates = logic_checker.extract_candidates(prompt)
            if candidates and len(candidates) == 1:
                return True, 'logic_checker', candidates[0]

        return False, '', None

    def select_model(self, category: str,
                    available_models: List[str]) -> Tuple[Optional[str], str]:
        """
        Select the best model for a category from available models.

        Routing hierarchy (Fireworks-only):
        1. Model with best historical performance for category
        2. Model with lowest average tokens for category
        3. First available model (as last resort)

        There is no local-model branch in this function. This is intentional:
        the hackathon rule states ALL inference must go through
        FIREWORKS_BASE_URL, and local tokens count as zero for scoring. A
        local-routing branch here would be a real disqualification risk if
        ever reachable, so it has been removed rather than disabled.

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

        def sort_key(stats):
            has_history = 1 if stats['has_category_history'] else 0
            return (-has_history, -stats['success_rate'], stats['avg_total_tokens'])

        model_stats.sort(key=sort_key)

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

        classification = self._classifier.classify(task_id, prompt)
        category = classification['category']

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
        """Route a batch of tasks."""
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
            if decision.category not in summary['by_category']:
                summary['by_category'][decision.category] = 0
            summary['by_category'][decision.category] += 1

            if decision.selected_model:
                if decision.selected_model not in summary['by_model']:
                    summary['by_model'][decision.selected_model] = 0
                summary['by_model'][decision.selected_model] += 1

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
