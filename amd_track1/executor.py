"""
Executor

Main execution engine that orchestrates the complete workflow:
- Input validation
- Task classification
- Routing
- Model execution (via Fireworks)
- Validation
- Retry/Escalation
- Output generation
"""

import json
import os
import random
import sys
import time
from typing import Any, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

from .input_validation import InputValidator, input_validator
from .classifier import TaskClassifier, get_classifier
from .model_registry import ModelRegistry, get_model_registry
from .model_roles import get_solver_model, get_verifier_model, is_verifier_available, reset_model_cache
from .router import TaskRouter, get_router, RoutingDecision
from .prompt_builder import PromptBuilder, get_prompt_builder
from .category_validator import CategoryValidator, get_category_validator
from .retry_policy import RetryManager, get_retry_manager
from .tools.submission_validator import submission_validator
from .verifier import (
    should_use_verifier,
    call_verifier_once,
    HIGH_RISK_CATEGORIES
)
from .local_client import LocalInferenceClient, get_local_client, is_local_mode_enabled
from .remote_mode import get_remote_mode, is_remote_allowed, is_rescue_mode, is_always_remote


@dataclass
class ExecutionResult:
    """Result of executing a single task."""
    task_id: str
    answer: Optional[str]
    category: str
    model_used: Optional[str]
    success: bool
    validation_errors: List[str] = field(default_factory=list)
    model_error: Optional[str] = None
    attempt_count: int = 0
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    latency: Optional[float] = None
    
    def to_output_dict(self) -> Dict[str, str]:
        """Convert to output format (only task_id and answer)."""
        return {
            'task_id': self.task_id,
            'answer': self.answer or ''
        }


class FireworksClient:
    """Client for Fireworks API."""

    TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}
    PERMANENT_STATUS_CODES = {400, 401, 404, 422}
    
    def __init__(self, api_key: Optional[str] = None, 
                 base_url: Optional[str] = None,
                 max_transport_retries: int = 5,
                 transport_retry_base_delay: float = 1.0,
                 transport_retry_max_delay: float = 30.0):
        """
        Initialize Fireworks client.
        
        Args:
            api_key: FIREWORKS_API_KEY
            base_url: FIREWORKS_BASE_URL
        """
        self.api_key = api_key or os.environ.get('FIREWORKS_API_KEY', '')
        self.base_url = base_url or os.environ.get('FIREWORKS_BASE_URL', '')
        self.max_transport_retries = max(1, max_transport_retries)
        self.transport_retry_base_delay = max(0.0, transport_retry_base_delay)
        self.transport_retry_max_delay = max(0.0, transport_retry_max_delay)
        
        if not self.api_key:
            raise ValueError("FIREWORKS_API_KEY not set")
        if not self.base_url:
            raise ValueError("FIREWORKS_BASE_URL not set")
    
    @classmethod
    def is_transient_error(cls, error: Optional[str]) -> bool:
        """Return True when an error string represents a retryable provider failure."""
        if not error:
            return False
        error_lower = error.lower()
        if "transport" in error_lower or "connection" in error_lower or "timeout" in error_lower:
            return True
        for status_code in cls.TRANSIENT_STATUS_CODES:
            if f"http {status_code}" in error_lower:
                return True
        return False

    def _retry_delay(self, retry_index: int) -> float:
        """Calculate bounded exponential backoff with small jitter."""
        if self.transport_retry_base_delay <= 0.0:
            return 0.0
        exponential = self.transport_retry_base_delay * (2 ** retry_index)
        jitter = random.uniform(0.0, min(1.0, self.transport_retry_base_delay))
        return min(self.transport_retry_max_delay, exponential + jitter)

    def infer(self, model_id: str, prompt: str,
              timeout: float = 300.0) -> Tuple[Optional[str], Optional[str], Optional[int], Optional[int], Optional[float]]:
        """
        Run inference with a model.
        
        Args:
            model_id: The model to use
            prompt: The prompt to send
            timeout: Timeout in seconds
            
        Returns:
            Tuple of (answer, error, input_tokens, output_tokens, latency)
        """
        import requests
        
        start_time = time.time()
        deadline = start_time + timeout

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        payload = {
            'model': model_id,
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': 4096,
            'temperature': 0.0,
            'response_format': {'type': 'text'}
        }

        last_error = None

        for transport_attempt in range(self.max_transport_retries):
            remaining = deadline - time.time()
            if remaining <= 0:
                latency = time.time() - start_time
                error_msg = last_error or f"Transport timeout: exceeded {timeout:.2f}s model-call budget"
                return None, error_msg, None, None, latency

            try:
                response = requests.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=remaining
                )

                latency = time.time() - start_time

                if response.status_code != 200:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    last_error = error_msg

                    if response.status_code in self.TRANSIENT_STATUS_CODES:
                        if transport_attempt == self.max_transport_retries - 1:
                            return None, error_msg, None, None, latency
                        delay = self._retry_delay(transport_attempt)
                        if delay > 0.0:
                            sleep_for = min(delay, max(0.0, deadline - time.time()))
                            if sleep_for > 0.0:
                                time.sleep(sleep_for)
                        continue

                    return None, error_msg, None, None, latency

                data = response.json()

                # Extract answer
                if 'choices' in data and len(data['choices']) > 0:
                    answer = data['choices'][0].get('message', {}).get('content', '')
                else:
                    answer = ''

                # Extract token counts
                input_tokens = data.get('usage', {}).get('prompt_tokens')
                output_tokens = data.get('usage', {}).get('completion_tokens')

                return answer, None, input_tokens, output_tokens, latency

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                latency = time.time() - start_time
                last_error = f"Transport error: {e}"
                if transport_attempt == self.max_transport_retries - 1:
                    return None, last_error, None, None, latency
                delay = self._retry_delay(transport_attempt)
                if delay > 0.0:
                    sleep_for = min(delay, max(0.0, deadline - time.time()))
                    if sleep_for > 0.0:
                        time.sleep(sleep_for)
                continue
            except Exception as e:
                latency = time.time() - start_time
                return None, str(e), None, None, latency

        latency = time.time() - start_time
        return None, last_error or "Transport retry exhausted", None, None, latency


class TaskExecutor:
    """Main task executor."""
    
    def __init__(self, skills_dir: Optional[str] = None,
                 api_key: Optional[str] = None,
                 base_url: Optional[str] = None,
                 max_concurrency: int = 4,
                 local_client: Optional[LocalInferenceClient] = None):
        """
        Initialize executor.
        
        Args:
            skills_dir: Directory containing skill definitions
            api_key: Fireworks API key (defaults to env)
            base_url: Fireworks base URL (defaults to env)
            max_concurrency: Maximum concurrent requests
            local_client: Optional local inference client for local-first mode
        """
        self._skills_dir = skills_dir
        self._max_concurrency = max_concurrency
        
        # Initialize components
        self._validator = input_validator
        self._classifier = get_classifier(skills_dir)
        self._registry = get_model_registry()
        self._router = get_router(skills_dir)
        self._prompt_builder = get_prompt_builder(skills_dir)
        self._category_validator = get_category_validator()
        self._retry_manager = get_retry_manager()
        
        # Initialize Fireworks client (remote fallback)
        self._fireworks_client = None
        if api_key and base_url:
            self._fireworks_client = FireworksClient(api_key, base_url)
        
        # Initialize local client (primary when available)
        self._local_client = local_client
        
        # Load skills
        if skills_dir:
            self._classifier.load_skills(skills_dir)
    
    def initialize(self, allowed_models: Optional[str] = None) -> bool:
        """
        Initialize from environment.
        
        Args:
            allowed_models: Override ALLOWED_MODELS
            
        Returns:
            True if initialization succeeded
        """
        # Initialize model registry
        if allowed_models:
            success = self._registry.initialize(allowed_models)
        else:
            success = self._registry.initialize()
        
        if not success:
            # In local-first mode, we can proceed with just the local model
            if self._local_client is not None and self._local_client.is_available():
                # Register local model in registry
                local_model_id = self._local_client.model_id
                if local_model_id not in self._registry._models:
                    from .model_registry import ModelRecord
                    self._registry._models[local_model_id] = ModelRecord(
                        model_id=local_model_id,
                        available=True,
                        successful_probe=True
                    )
                self._registry._initialized = True
                return True
            return False
        
        # Initialize Fireworks client if not done (only if remote models are expected)
        if self._fireworks_client is None:
            try:
                self._fireworks_client = FireworksClient()
            except ValueError:
                # Fireworks not configured; ok if local client is available
                if self._local_client is None or not self._local_client.is_available():
                    return False
        
        # Register local model if available
        if self._local_client is not None and self._local_client.is_available():
            local_model_id = self._local_client.model_id
            if local_model_id not in self._registry._models:
                from .model_registry import ModelRecord
                self._registry._models[local_model_id] = ModelRecord(
                    model_id=local_model_id,
                    available=True,
                    successful_probe=True
                )
        
        return True
    
    def _select_inference_client(self, model_id: Optional[str]) -> Optional[Any]:
        """
        Select the appropriate inference client for a model.
        
        Respects AMD_REMOTE_MODE:
        - off:     local only, never Fireworks
        - rescue:  local first, Fireworks only on failure/escalation
        - always:  Fireworks primary (debug only)
        
        Args:
            model_id: The requested model ID
            
        Returns:
            FireworksClient or LocalInferenceClient (both have .infer method)
        """
        mode = get_remote_mode()
        local_available = (
            self._local_client is not None and self._local_client.is_available()
        )
        local_model_id = (
            self._local_client.model_id if self._local_client is not None else None
        )

        # Mode: off — never use Fireworks
        if mode == "off":
            if local_available:
                return self._local_client.fireworks_client
            return None

        # Mode: always — prefer Fireworks, local as last resort
        if mode == "always":
            if self._fireworks_client is not None:
                return self._fireworks_client
            if local_available:
                return self._local_client.fireworks_client
            return None

        # Mode: rescue (default) — local first, then Fireworks fallback
        if local_available:
            # Use local if: no specific model, model matches local, or Fireworks unavailable
            if (
                model_id is None
                or model_id == local_model_id
                or not self._fireworks_client
            ):
                return self._local_client.fireworks_client

        # Fall back to Fireworks for rescue/always when local doesn't match or unavailable
        if self._fireworks_client is not None:
            return self._fireworks_client

        # Last resort: local even if not preferred
        if local_available:
            return self._local_client.fireworks_client

        return None
    
    def execute_task(self, task: Dict[str, str],
                     max_attempts: int = 2,
                     deadline: Optional[float] = None) -> ExecutionResult:
        """
        Execute a single task through the complete workflow.
        
        Args:
            task: Task dict with task_id and prompt
            max_attempts: Maximum attempts per task
            
        Returns:
            ExecutionResult
        """
        task_id = task['task_id']
        prompt = task['prompt']
        
        # Initialize retry state
        classification = self._classifier.classify(task_id, prompt)
        category = classification['category']
        
        # Initialize retry state
        retry_state = self._retry_manager.initialize_task(task_id, category)
        
        # Route the task
        routing_decision = self._router.route_task(task)
        
        # Check if deterministic tool can solve
        if routing_decision.selected_model is None and 'tool' in routing_decision.routing_reason:
            # Extract tool name from reason
            import re
            match = re.search(r'tool\s+(\w+)', routing_decision.routing_reason)
            if match:
                tool_name = match.group(1)
                # For now, we'll just use the tool result directly
                # In a full implementation, we'd call the tool
                if tool_name == 'arithmetic_evaluator':
                    from .tools import ArithmeticEvaluator
                    try:
                        # Try to evaluate the prompt as an expression
                        import re
                        matches = re.findall(r'[\d]+[\s]*[+\-*/%^**][\s]*[\d]+', prompt)
                        if matches:
                            result = ArithmeticEvaluator().evaluate_to_string(matches[0])
                            return ExecutionResult(
                                task_id=task_id,
                                answer=result,
                                category=category,
                                model_used=None,
                                success=True,
                                attempt_count=1
                            )
                    except:
                        pass
        
        # Get available models
        available_models = self._registry.get_available_models()
        
        if not available_models:
            return ExecutionResult(
                task_id=task_id,
                answer=None,
                category=category,
                model_used=None,
                success=False,
                model_error="No models available",
                attempt_count=0
            )
        
        # Execute with retries
        last_error = None
        last_validation_errors = []
        
        for attempt in range(max_attempts):
            # Select model
            if attempt == 0:
                model_id = routing_decision.selected_model
                if model_id is None:
                    # Use solver model from model_roles, fallback to first available
                    model_id = get_solver_model() or (available_models[0] if available_models else None)
                if model_id is None:
                    # Fallback to first available model
                    model_id = available_models[0] if available_models else None
            else:
                # Get next model from retry manager
                model_id = self._retry_manager.get_next_model(
                    task_id, routing_decision.selected_model or available_models[0], category
                )
                if model_id is None:
                    break  # No more models to try
            
            # Build prompt
            prompt_info = self._prompt_builder.build_prompt(task_id, prompt, category)
            constructed_prompt = prompt_info['prompt']

            if deadline is not None:
                remaining_budget = deadline - time.time()
                if remaining_budget <= 0:
                    last_error = "Total execution timeout exceeded"
                    break
                call_timeout = min(300.0, remaining_budget)
            else:
                call_timeout = 300.0

            # Determine which client to use: local-first, then remote fallback
            client = self._select_inference_client(model_id)
            if client is None:
                last_error = "No inference client available (local or remote)"
                break

            # Ensure model_id is valid for the selected client
            if model_id:
                effective_model_id = model_id
            elif self._local_client is not None and client is self._local_client.fireworks_client:
                effective_model_id = self._local_client.model_id
            else:
                effective_model_id = 'unknown'

            # Execute model. Client owns transient transport/status retries
            # so these do not consume the correction-retry budget below.
            answer, model_error, input_tokens, output_tokens, latency = \
                client.infer(
                    effective_model_id, constructed_prompt, timeout=call_timeout
                )

            if model_error:
                last_error = model_error

                if FireworksClient.is_transient_error(model_error):
                    break

                if model_id is not None:
                    self._retry_manager.record_attempt(
                        task_id, model_id, answer, None, model_error
                    )
                
                # Check if we should retry
                should_retry, reason = self._retry_manager.should_retry(
                    task_id, [], model_error
                )
                
                if not should_retry:
                    break
                
                # Update routing decision for next attempt
                routing_decision.selected_model = model_id
                continue
            
            # Validate answer
            if answer:
                valid, validation_errors = self._category_validator.validate(
                    category, prompt, answer
                )
                
                if valid:
                    if model_id is not None:
                        self._retry_manager.record_attempt(
                            task_id, model_id, answer, [], None
                        )

                        # Record successful result in registry
                        self._registry.record_category_result(
                            model_id, category,
                            success=True,
                            input_tokens=input_tokens,
                            output_tokens=output_tokens,
                            latency=latency
                        )
                    
                    # Check if verifier is needed (high-risk category or validation errors)
                    # For valid answers, only high-risk categories trigger verifier
                    if should_use_verifier(task_id, category, answer, []):
                        if is_verifier_available():
                            verifier_result = call_verifier_once(
                                task_id=task_id,
                                category=category,
                                prompt=prompt,
                                candidate_answer=answer,
                                validation_errors=[],
                                fireworks_client=self._fireworks_client
                            )
                            if verifier_result.get("success") and verifier_result.get("validated"):
                                # Use verifier's answer if it passed validation
                                answer = verifier_result["final_answer"]
                                # Record verifier usage in registry
                                verifier_model = get_verifier_model()
                                if verifier_model:
                                    self._registry.record_category_result(
                                        verifier_model, category,
                                        success=True,
                                        input_tokens=None,
                                        output_tokens=None,
                                        latency=None
                                    )
                    
                    return ExecutionResult(
                        task_id=task_id,
                        answer=answer,
                        category=category,
                        model_used=model_id,
                        success=True,
                        attempt_count=attempt + 1,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        latency=latency
                    )
                else:
                    last_validation_errors = validation_errors

                    if model_id is not None:
                        self._retry_manager.record_attempt(
                            task_id, model_id, answer, validation_errors, None
                        )
                        
                        # Record failure in registry
                        self._registry.record_category_result(
                            model_id, category,
                            success=False,
                            input_tokens=input_tokens,
                            output_tokens=output_tokens,
                            latency=latency
                        )
                    
                    # Check if verifier is needed for invalid answers
                    # Always try verifier for validation failures
                    verifier_used = False
                    if should_use_verifier(task_id, category, answer, validation_errors):
                        if is_verifier_available():
                            verifier_result = call_verifier_once(
                                task_id=task_id,
                                category=category,
                                prompt=prompt,
                                candidate_answer=answer,
                                validation_errors=validation_errors,
                                fireworks_client=self._fireworks_client
                            )
                            verifier_used = verifier_result.get("verifier_used", False)
                            if verifier_result.get("success") and verifier_result.get("validated"):
                                # Verifier produced a valid answer - use it
                                answer = verifier_result["final_answer"]
                                # Record successful verifier result
                                verifier_model = get_verifier_model()
                                if verifier_model:
                                    self._registry.record_category_result(
                                        verifier_model, category,
                                        success=True,
                                        input_tokens=None,
                                        output_tokens=None,
                                        latency=None
                                    )
                                # Return with verifier's answer - no retry needed
                                return ExecutionResult(
                                    task_id=task_id,
                                    answer=answer,
                                    category=category,
                                    model_used=model_id,
                                    success=True,
                                    validation_errors=[],
                                    attempt_count=attempt + 1,
                                    input_tokens=input_tokens,
                                    output_tokens=output_tokens,
                                    latency=latency
                                )
                            elif verifier_result.get("final_answer") is not None:
                                # Verifier returned an answer but it failed validation
                                # Keep the solver's answer and continue to retry logic
                                pass
                    
                    # Check if we should retry
                    should_retry, reason = self._retry_manager.should_retry(
                        task_id, validation_errors, model_error
                    )
                    
                    if not should_retry:
                        break
                    
                    # Update routing decision
                    routing_decision.selected_model = model_id
            else:
                last_error = "Empty response from model"
                break
        
        # All attempts failed
        return ExecutionResult(
            task_id=task_id,
            answer=None,
            category=category,
            model_used=routing_decision.selected_model,
            success=False,
            validation_errors=last_validation_errors,
            model_error=last_error,
            attempt_count=retry_state.get_attempt_count()
        )
    
    def execute_batch(self, tasks: List[Dict[str, str]],
                      max_concurrency: Optional[int] = None,
                      deadline: Optional[float] = None) -> List[ExecutionResult]:
        """
        Execute a batch of tasks.
        
        Args:
            tasks: List of task dicts
            max_concurrency: Override max concurrency
            
        Returns:
            List of ExecutionResult objects
        """
        concurrency = max_concurrency or self._max_concurrency
        results = []
        
        # Use ThreadPoolExecutor for concurrent execution
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = {
                executor.submit(self.execute_task, task, deadline=deadline): task
                for task in tasks
            }
            
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
        
        return results
    
    def process_input(self, input_path: str = '/input/tasks.json',
                      output_path: str = '/output/results.json',
                      total_timeout: Optional[float] = None) -> Tuple[bool, List[str]]:
        """
        Process input tasks and write output results.
        
        Args:
            input_path: Path to input tasks.json
            output_path: Path to output results.json
            
        Returns:
            Tuple of (success, errors)
        """
        errors = []
        deadline = time.time() + total_timeout if total_timeout is not None else None
        
        # Step 1: Read and validate input
        valid, tasks, malformed, read_error = self._validator.validate_from_file(input_path)
        
        if read_error:
            errors.append(f"Error reading input: {read_error}")
            return False, errors
        
        if not valid:
            validation_errors = self._validator.get_errors()
            errors.extend(validation_errors)
            # Still try to process valid tasks
            if not tasks:
                return False, errors
        
        # Log malformed tasks (but continue with valid ones)
        if malformed:
            for m in malformed:
                errors.append(f"Malformed task at index {m['index']}: {m['error']}")
        
        # Step 2: Initialize components
        if not self._registry._initialized:
            success = self.initialize()
            if not success:
                errors.append("Failed to initialize model registry")
                return False, errors
        
        # Step 3: Execute tasks
        results = self.execute_batch(tasks, deadline=deadline)
        
        # Step 4: Collect successful results
        output_results = []
        for result in results:
            if result.success and result.answer:
                output_results.append(result.to_output_dict())
            else:
                errors.append(f"Task {result.task_id} failed: {result.model_error or result.validation_errors}")
        
        # Step 5: Validate output
        valid_output, output_errors = submission_validator.validate_results_structure(output_results)
        errors.extend(output_errors)
        
        if not valid_output:
            return False, errors
        
        # Step 6: Check coverage
        input_task_ids = {t['task_id'] for t in tasks}
        output_task_ids = {r['task_id'] for r in output_results}
        
        missing = input_task_ids - output_task_ids
        if missing:
            errors.extend(f"Missing result for task: {tid}" for tid in missing)
            return False, errors
        
        # Step 7: Atomically write output
        json_str = submission_validator.create_valid_output(output_results)
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except Exception as e:
                errors.append(f"Failed to create output directory: {e}")
                return False, errors
        
        # Atomic write
        success = submission_validator.atomic_write(output_path, json_str)
        if not success:
            errors.append("Failed to write output atomically")
            return False, errors
        
        return True, errors


# Singleton instance
_executor_instance = None

def get_executor(skills_dir: Optional[str] = None,
                api_key: Optional[str] = None,
                base_url: Optional[str] = None,
                max_concurrency: int = 4) -> TaskExecutor:
    """Get or create the singleton executor instance."""
    global _executor_instance
    if _executor_instance is None:
        local_client = get_local_client() if is_local_mode_enabled() else None
        _executor_instance = TaskExecutor(skills_dir, api_key, base_url, max_concurrency, local_client)
    return _executor_instance
