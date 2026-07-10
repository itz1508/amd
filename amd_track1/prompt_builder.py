"""
Prompt Construction

Builds category-specific minimal prompts for model inference.
"""

import json
from typing import Any, Callable, Dict, Optional, Tuple
from .classifier import TaskClassifier, get_classifier


class PromptBuilder:
    """Builds minimal prompts for each category."""
    
    # Category-specific prompt templates
    PROMPT_TEMPLATES = {
        'factual_knowledge': {
            'base': "Answer the following question directly and concisely.\n\n{prompt}",
            'direct': "{prompt}",
            'explain': "Answer the question. Provide a brief explanation only if explicitly requested.\n\n{prompt}"
        },
        'mathematical_reasoning': {
            'base': "Solve the following mathematical problem. Return only the final answer in numeric form.\n\n{prompt}",
            'show_work': "Solve step by step and show your work.\n\n{prompt}",
            'direct': "{prompt}"
        },
        'sentiment_classification': {
            'base': "Classify the sentiment of the following text. Use only one of these labels: positive, negative, neutral.\n\n{prompt}",
            'with_justification': "Classify the sentiment of the following text and provide a brief justification. Use only: positive, negative, neutral.\n\n{prompt}",
            'direct': "Classify sentiment. Only respond with: positive, negative, or neutral.\n\n{prompt}"
        },
        'text_summarisation': {
            'base': "Summarize the following text. Preserve all key information.\n\n{prompt}",
            'word_limit': "Summarize the following text in {limit} words or less.\n\n{prompt}",
            'sentence_limit': "Summarize the following text in {limit} sentences or less.\n\n{prompt}",
            'bullet_points': "Summarize the following text as bullet points.\n\n{prompt}"
        },
        'named_entity_recognition': {
            'base': "Extract all named entities from the following text. Return as a JSON array with 'type' and 'value' fields. Supported types: person, organization, location, date.\n\n{prompt}",
            'json_format': "Extract entities from the following text and return as a JSON array. Each entity must have 'type' (person/organization/location/date) and 'value' fields.\n\n{prompt}",
            'text_format': "Extract entities from the following text. Format each as: type: value\n\n{prompt}"
        },
        'code_debugging': {
            'base': "Identify the bug in the following code and return the corrected version.\n\n{prompt}",
            'with_explanation': "Identify the bug, explain it briefly, and return the corrected code.\n\n{prompt}",
            'direct_fix': "Return only the corrected code without explanation.\n\n{prompt}"
        },
        'logical_reasoning': {
            'base': "Solve the following logical reasoning problem. Provide the correct answer.\n\n{prompt}",
            'multiple_choice': "Solve the following logical reasoning problem. Select exactly one correct answer from the options provided.\n\n{prompt}",
            'with_explanation': "Solve the logical reasoning problem and explain your reasoning.\n\n{prompt}",
            'direct': "Solve: {prompt}"
        },
        'code_generation': {
            'base': "Write code to solve the following task. Return only the code.\n\n{prompt}",
            'with_signature': "Write a function with the following signature:\n{signature}\n\n{prompt}",
            'with_example': "Write code based on the following example.\n\n{prompt}",
            'complete_code': "Complete the following code:\n\n{prompt}"
        }
    }
    
    # Category-specific output shape specifications
    OUTPUT_SHAPES = {
        'factual_knowledge': "string (direct answer)",
        'mathematical_reasoning': "numeric value or mathematical expression",
        'sentiment_classification': "one of: positive, negative, neutral",
        'text_summarisation': "string (summary text)",
        'named_entity_recognition': "JSON array of {type, value} objects",
        'code_debugging': "code string (corrected code)",
        'logical_reasoning': "string (selected answer or solution)",
        'code_generation': "code string"
    }
    
    def __init__(self, skills_dir: Optional[str] = None):
        """
        Initialize prompt builder.
        
        Args:
            skills_dir: Directory containing skill definitions
        """
        self._classifier = get_classifier(skills_dir)
        self._skills_dir = skills_dir
        # Ensure skills are loaded even if classifier singleton was created without them
        if skills_dir and not self._classifier._skills:
            self._classifier.load_skills(skills_dir)
    
    def _select_template_variant(self, category: str, prompt: str) -> str:
        """
        Select the best template variant for a prompt.
        
        Args:
            category: The task category
            prompt: The task prompt
            
        Returns:
            Selected template key
        """
        skill = self._classifier.get_skill_definition(category)
        prompt_procedure = skill.get('prompt_procedure', {})
        default = prompt_procedure.get('default')
        if default:
            return default
        return 'base'

    def _get_skill_template(self, category: str, template_key: str) -> Optional[str]:
        """Return a prompt template from loaded skill JSON when available."""
        skill = self._classifier.get_skill_definition(category)
        prompt_procedure = skill.get('prompt_procedure', {})
        if template_key == 'base_template':
            return prompt_procedure.get('base_template')
        variants = prompt_procedure.get('variants', {})
        if template_key in variants:
            return variants[template_key]
        return prompt_procedure.get('base_template')
    
    def _extract_parameters(self, prompt: str, category: str) -> Dict[str, Any]:
        """
        Extract parameters from prompt for template filling.
        
        Args:
            prompt: The task prompt
            category: The task category
            
        Returns:
            Dict of parameters for template
        """
        params = {}
        
        # Extract code signature for code generation
        if category == 'code_generation':
            # Look for function signature patterns
            import re
            match = re.search(r'(def\s+\w+\s*\()', prompt)
            if match:
                params['signature'] = match.group(0)
        
        # Extract limits for summarization
        if category == 'text_summarisation':
            import re
            word_match = re.search(r'(\d+)\s+words?', prompt, re.IGNORECASE)
            sentence_match = re.search(r'(\d+)\s+sentences?', prompt, re.IGNORECASE)
            
            if word_match:
                params['limit'] = word_match.group(1)
            elif sentence_match:
                params['limit'] = sentence_match.group(1)
        
        return params
    
    def build_prompt(self, task_id: str, prompt: str, category: Optional[str] = None) -> Dict[str, Any]:
        """
        Build a complete prompt for a task.
        
        Args:
            task_id: The task identifier
            prompt: The original prompt
            category: Optional pre-determined category
            
        Returns:
            Dict with prompt information:
            - category: The category
            - prompt: The constructed prompt
            - output_shape: Expected output shape
            - instructions: Any additional instructions
        """
        # Classify if category not provided
        if category is None:
            classification = self._classifier.classify(task_id, prompt)
            category = classification['category']
        
        # Get template. Skill JSON is the routing/prompt contract; static
        # templates remain a fallback for missing or malformed skill files.
        templates = self.PROMPT_TEMPLATES.get(category, {'base': "{prompt}"})
        template_key = self._select_template_variant(category, prompt)
        template = self._get_skill_template(category, template_key)
        if not template:
            template = templates.get(template_key, templates['base'])
        
        # Extract parameters
        params = self._extract_parameters(prompt, category)
        
        # Fill template
        filled_prompt = template.format(prompt=prompt, **params)
        
        # Clean up any double newlines
        filled_prompt = filled_prompt.replace('\n\n\n', '\n\n')
        
        return {
            'category': category,
            'prompt': filled_prompt,
            'output_shape': self._get_output_shape(category),
            'instructions': self._get_category_instructions(category)
        }

    def _get_output_shape(self, category: str) -> str:
        """Get expected output shape from skill JSON with static fallback."""
        skill = self._classifier.get_skill_definition(category)
        return skill.get('expected_answer_shape') or self.OUTPUT_SHAPES.get(category, 'string')
    
    def _get_category_instructions(self, category: str) -> str:
        """
        Get category-specific instructions.
        
        Args:
            category: The task category
            
        Returns:
            Instruction string
        """
        instructions = {
            'factual_knowledge': (
                "Answer directly and concisely. "
                "Do not provide explanations unless explicitly requested. "
                "Do not fabricate information or citations."
            ),
            'mathematical_reasoning': (
                "Solve accurately. Return only the final numeric answer. "
                "Do not include step-by-step working unless requested."
            ),
            'sentiment_classification': (
                "Use only the labels: positive, negative, neutral. "
                "Add justification only when explicitly requested."
            ),
            'text_summarisation': (
                "Preserve all key information. "
                "Do not add information not present in the source. "
                "Obey any word or sentence limits specified."
            ),
            'named_entity_recognition': (
                "Extract all entities. Use only the types: person, organization, location, date. "
                "Return as JSON array with type and value fields."
            ),
            'code_debugging': (
                "Identify the actual bug. Return the corrected code. "
                "Preserve the original function/class signature and interface."
            ),
            'logical_reasoning': (
                "Satisfy every stated constraint. "
                "Select exactly one answer when multiple choices are provided. "
                "Do not contradict any conditions."
            ),
            'code_generation': (
                "Implement the requested function. "
                "Preserve the requested signature. "
                "Avoid unrelated scaffolding or extra output."
            )
        }
        
        return instructions.get(category, "Provide a direct and accurate answer.")
    
    def build_batch_prompts(self, tasks: list) -> list:
        """
        Build prompts for a batch of tasks.
        
        Args:
            tasks: List of task dicts with task_id and prompt
            
        Returns:
            List of prompt dicts
        """
        results = []
        for task in tasks:
            result = self.build_prompt(task['task_id'], task['prompt'])
            results.append(result)
        return results


# Singleton instance
_prompt_builder_instance = None

def get_prompt_builder(skills_dir: Optional[str] = None) -> PromptBuilder:
    """Get or create the singleton prompt builder instance."""
    global _prompt_builder_instance
    if _prompt_builder_instance is None:
        _prompt_builder_instance = PromptBuilder(skills_dir)
    return _prompt_builder_instance
