"""
Eight-Category Classifier

Deterministic-first classifier for the eight AMD Track 1 categories.
Uses lexical and structural signals first, falls back to model only when needed.
"""

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path


class TaskClassifier:
    """Eight-category task classifier."""
    
    ALLOWED_CATEGORIES = [
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
    
    def __init__(self, skills_dir: Optional[str] = None):
        """
        Initialize classifier.
        
        Args:
            skills_dir: Directory containing skill JSON files
        """
        self._skills = {}
        self._skill_triggers = {}
        self._skill_anti_triggers = {}
        
        # Load skills if directory provided
        if skills_dir:
            self.load_skills(skills_dir)
    
    def load_skills(self, skills_dir: str) -> bool:
        """
        Load skill definitions from directory.
        
        Args:
            skills_dir: Directory path containing skill JSON files
            
        Returns:
            True if all skills loaded successfully
        """
        try:
            skills_path = Path(skills_dir)
            for skill_file in skills_path.glob('*.json'):
                with open(skill_file, 'r', encoding='utf-8') as f:
                    skill_data = json.load(f)
                    skill_id = skill_data.get('skill_id', skill_file.stem)
                    self._skills[skill_id] = skill_data
                    
                    # Index triggers and anti-triggers
                    triggers = skill_data.get('trigger_signals', [])
                    anti_triggers = skill_data.get('should_not_trigger_signals', [])
                    
                    self._skill_triggers[skill_id] = [t.lower() for t in triggers]
                    self._skill_anti_triggers[skill_id] = [t.lower() for t in anti_triggers]
            
            return True
        except Exception as e:
            return False
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        return text.lower().strip()
    
    def _count_signal_matches(self, text: str, signals: List[str]) -> int:
        """Count how many signals match in text."""
        count = 0
        text_lower = self._normalize_text(text)
        for signal in signals:
            if signal in text_lower:
                count += 1
        return count
    
    def _get_trigger_counts(self, prompt: str) -> Dict[str, int]:
        """Get trigger signal counts for each category."""
        counts = {}
        for category, triggers in self._skill_triggers.items():
            counts[category] = self._count_signal_matches(prompt, triggers)
        return counts
    
    def _get_anti_trigger_counts(self, prompt: str) -> Dict[str, int]:
        """Get anti-trigger signal counts for each category."""
        counts = {}
        for category, anti_triggers in self._skill_anti_triggers.items():
            counts[category] = self._count_signal_matches(prompt, anti_triggers)
        return counts
    
    # Built-in fallback classification rules (used when skills are not loaded)
    _BUILTIN_RULES: list[tuple[str, str]] = [
        # mathematical_reasoning — arithmetic, calculation
        (r'(what\s+is\s+[\d\s+\-*/().]+\??)|(calculate\s+[\d\s+\-*/().]+)|(compute\s+[\d\s+\-*/().]+)|(solve\s+[\d\s+\-*/().]+)|(evaluate\s+[\d\s+\-*/().]+)|(^\s*[\d\s+\-*/().]+\s*[=]?\s*$)|(\b\d+\s*[\+\-\*/]\s*\d+\b)|(\b(plus|minus|times|divided\s+by)\b)|(\b(arithmetic|math(ematical)?|algebra|calculus|equation)\b)', 'mathematical_reasoning'),
        # sentiment_classification
        (r'(classify\s+(this\s+)?(review|text|sentence|statement)\s+as\s+(positive|negative|neutral))|(sentiment\s+(analysis|classification|detection))|(is\s+(this|the)\s+(review|text|sentence)\s+(positive|negative|neutral)\?)|(determine\s+(the\s+)?sentiment)|(positive\s+or\s+negative\s+(review|sentiment))|(what\s+is\s+the\s+sentiment)', 'sentiment_classification'),
        # named_entity_recognition
        (r'(named\s+entity\s+(recognition|extraction|detection))|(\bNER\b)|(extract\s+(the\s+)?(named\s+)?entities)|(identify\s+(the\s+)?(named\s+)?entities)|(find\s+(all\s+)?(the\s+)?(named\s+)?entities)|(entity\s+(recognition|extraction|span|label))|(what\s+(are|were)\s+the\s+(named\s+)?entities)', 'named_entity_recognition'),
        # code_generation
        (r'(write|generate|create|implement|code)\s+(a\s+)?(function|method|class|program|script|code|module|api|endpoint)|(generate\s+code\s+(for|to|that))|(write\s+(a\s+)?(python|javascript|typescript|java|go|rust|c\+\+|ruby|php|sql|bash|shell)\s+(function|script|program|code))|(implement\s+(a\s+)?(function|method|class|interface|algorithm))|(create\s+(a\s+)?(function|method|class|component|module)\s+(that|to|for|which))|(build\s+(a\s+)?(function|api|endpoint|service|application))', 'code_generation'),
        # code_debugging
        (r'(debug|fix|repair|correct)\s+(this\s+)?(code|function|method|program|script|bug|error|issue)|(find\s+(the\s+)?(bug|error|issue|problem)\s+in)|(what\s+is\s+wrong\s+with\s+(this\s+)?(code|function|program))|(why\s+(does|is)\s+(this\s+)?(code|function|program)\s+(not\s+)?(work|fail|error|crash))|(fix\s+(the\s+)?(bug|error|issue|problem))|(debugging|troubleshoot|diagnose)\s+(this\s+)?(code|issue|problem)', 'code_debugging'),
        # logical_reasoning
        (r'(logical\s+(reasoning|puzzle|deduction|inference|problem))|(reason\s+(about|through|logically))|(deduce|infer|conclude)\s+(the\s+)?(answer|result|conclusion|outcome)|(if\s+.+\s+then\s+.+\?)|(which\s+(of\s+the\s+following|statement|conclusion)\s+(is|must\s+be)\s+(true|false|valid|invalid))|(syllogism|premise|conclusion)\s+(is|are)|(logical\s+(fallacy|contradiction|consistency))|(puzzle|riddle|brain\s+teaser)\s+(about|involving|where)', 'logical_reasoning'),
        # text_summarisation
        (r'(summarize|summarise|summary|condense|abstract)\s+(this|the|a|an)|(give\s+(me\s+)?(a\s+)?summary\s+(of|for))|(provide\s+(a\s+)?summary\s+(of|for))|(write\s+(a\s+)?summary\s+(of|for|about))|(in\s+(a\s+)?(few|short|brief)\s+(sentences|words|paragraph))|(tl;dr|tldr)|(key\s+points?\s+(of|from|in))|(main\s+(idea|point|argument|takeaway))', 'text_summarisation'),
        # factual_knowledge — catch-all for what/who/when/where/why/how questions
        (r'(what\s+(is|are|was|were)\s+(the|a|an)?\s*.+)|(who\s+(is|are|was|were)\s+.+)|(when\s+(did|was|is|are|were)\s+.+)|(where\s+(is|are|was|were|did)\s+.+)|(define\s+.+)|(definition\s+of\s+.+)|(explain\s+(the|a|an|what|how|why)\s+.+)|(how\s+(many|much|long|far|often|does|do|is|are|can|did|was|were)\s+.+)|(describe\s+(the|a|an)\s+.+)|(list\s+(the|all|some)\s+.+)|(tell\s+me\s+(about|the)\s+.+)|(what\s+(does|do)\s+.+\s+(mean|stand\s+for)\??)', 'factual_knowledge'),
    ]

    def _classify_deterministic(self, prompt: str) -> Dict[str, Any]:
        """
        Attempt deterministic classification using lexical signals.
        
        Args:
            prompt: The task prompt
            
        Returns:
            Classification result with category and confidence
        """
        trigger_counts = self._get_trigger_counts(prompt)
        anti_trigger_counts = self._get_anti_trigger_counts(prompt)
        
        # Check for structural patterns that override lexical signals
        # Mathematical expressions should strongly indicate mathematical_reasoning
        math_pattern = r'[\d]+[\s]*[+\-*/%^**][\s]*[\d]+'
        if re.search(math_pattern, prompt):
            # If we have a math expression, check if it's part of a question like "What is 2+2?"
            # These should be mathematical_reasoning, not factual_knowledge
            prompt_lower = self._normalize_text(prompt)
            question_starters = ['what is', 'what\'s', 'what are', 'how much is', 'how many is', 'calculate']
            if any(prompt_lower.startswith(q) or (q + ' ') in prompt_lower for q in question_starters):
                # Override to mathematical_reasoning if we have both question + math expression
                return {
                    'category': 'mathematical_reasoning',
                    'confidence': 1.0,
                    'signals': ['mathematical_expression', 'question_pattern'],
                    'method': 'structural_override'
                }
        
        # Find category with highest trigger count
        best_category = None
        best_count = 0
        
        for category, count in trigger_counts.items():
            if category == 'unknown':
                continue
            
            # Check if this category has anti-triggers that match
            if anti_trigger_counts.get(category, 0) > 0:
                # Has anti-triggers, reduce confidence
                count = max(0, count - anti_trigger_counts[category] * 2)
            
            if count > best_count:
                best_count = count
                best_category = category
        
        # Calculate confidence (0.0 to 1.0)
        # If we have a clear winner, confidence is high
        if best_count > 0:
            total_triggers = sum(trigger_counts.values())
            if total_triggers > 0:
                confidence = best_count / total_triggers
            else:
                confidence = 1.0  # Only this category has triggers
        else:
            confidence = 0.0
        
        # Extract signals that matched
        signals = []
        if best_category and best_category in self._skill_triggers:
            for signal in self._skill_triggers[best_category]:
                if signal in self._normalize_text(prompt):
                    signals.append(signal)
        
        # Fallback: if no skill-based match, use built-in rules
        if best_category is None or best_count == 0:
            prompt_lower = self._normalize_text(prompt)
            for pattern, category in self._BUILTIN_RULES:
                if re.search(pattern, prompt_lower, re.IGNORECASE):
                    return {
                        'category': category,
                        'confidence': 0.8,
                        'signals': ['builtin_rule_match'],
                        'method': 'builtin_fallback'
                    }
            # Ultimate fallback
            return {
                'category': 'factual_knowledge',
                'confidence': 0.5,
                'signals': [],
                'method': 'default_fallback'
            }
        
        return {
            'category': best_category if best_category else 'unknown',
            'confidence': confidence,
            'signals': signals,
            'method': 'deterministic'
        }
    
    def _apply_structural_analysis(self, prompt: str, category: str) -> float:
        """
        Apply structural analysis to adjust confidence.
        
        Args:
            prompt: The task prompt
            category: Current category
            
        Returns:
            Confidence adjustment (multiplier)
        """
        # Check for code blocks
        if '```' in prompt or 'def ' in prompt or 'function ' in prompt:
            if category in ['code_generation', 'code_debugging']:
                return 1.2  # Boost confidence
            elif category not in ['code_generation', 'code_debugging', 'unknown']:
                return 0.8  # Reduce confidence for non-code categories
        
        # Check for mathematical expressions
        if re.search(r'[\d]+[\s]*[+\-*/%^**][\s]*[\d]+', prompt) or \
           re.search(r'[\d]+[\s]*[=<>][\s]*[\d]+', prompt):
            if category == 'mathematical_reasoning':
                return 1.2
            elif category not in ['mathematical_reasoning', 'unknown']:
                return 0.8
        
        # Check for quotation marks (likely summarization or factual)
        quote_count = prompt.count('"') + prompt.count("'")
        if quote_count > 20:  # Lots of quotes, likely text to summarize
            if category == 'text_summarisation':
                return 1.2
        
        return 1.0
    
    def classify(self, task_id: str, prompt: str) -> Dict[str, Any]:
        """
        Classify a task into one of the eight categories.
        
        Args:
            task_id: The task identifier
            prompt: The task prompt
            
        Returns:
            Classification result dictionary with:
            - task_id: The task identifier
            - category: The classified category
            - confidence: Confidence score (0.0 to 1.0)
            - signals: List of matched signals
            - expected_answer_shape: Expected output shape
            - selected_skill: The selected skill ID
        """
        # Step 1: Try deterministic classification
        deterministic_result = self._classify_deterministic(prompt)
        
        # Step 2: Apply structural analysis
        confidence = deterministic_result['confidence']
        confidence *= self._apply_structural_analysis(prompt, deterministic_result['category'])
        confidence = min(1.0, max(0.0, confidence))
        
        category = deterministic_result['category']
        signals = deterministic_result['signals']
        
        # Step 3: Get expected answer shape and skill from definition
        skill_data = self._skills.get(category, {})
        expected_answer_shape = skill_data.get('expected_answer_shape', 'string')
        selected_skill = skill_data.get('skill_id', category)
        
        return {
            'task_id': task_id,
            'category': category,
            'confidence': round(confidence, 4),
            'signals': signals,
            'expected_answer_shape': expected_answer_shape,
            'selected_skill': selected_skill
        }
    
    def classify_batch(self, tasks: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Classify a batch of tasks.
        
        Args:
            tasks: List of task dicts with task_id and prompt
            
        Returns:
            List of classification results
        """
        results = []
        for task in tasks:
            result = self.classify(task['task_id'], task['prompt'])
            results.append(result)
        return results
    
    def get_category_from_classification(self, classification: Dict[str, Any]) -> str:
        """Extract category from classification result."""
        return classification.get('category', 'unknown')

    def get_skill_definition(self, category: str) -> Dict[str, Any]:
        """Get loaded skill definition for a category."""
        return self._skills.get(category, {})


# Singleton instance (lazy loading of skills)
_classifier_instance = None

def get_classifier(skills_dir: Optional[str] = None) -> TaskClassifier:
    """Get or create the singleton classifier instance."""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = TaskClassifier(skills_dir)
    return _classifier_instance
