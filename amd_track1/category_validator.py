"""
Category-Specific Validation

Validates answers based on their category.
"""

import json
import re
from typing import Any, Dict, List, Optional, Tuple
from .tools.arithmetic_evaluator import arithmetic_evaluator
from .tools.sentiment_validator import sentiment_validator
from .tools.summary_checker import summary_checker
from .tools.ner_validator import ner_validator
from .tools.code_checker import code_checker
from .tools.logic_checker import logic_checker


class CategoryValidator:
    """Validates answers by category."""
    
    def __init__(self):
        """Initialize validator."""
        pass
    
    def validate(self, category: str, prompt: str, answer: str) -> Tuple[bool, list]:
        """
        Validate an answer based on its category.
        
        Args:
            category: The task category
            prompt: The original prompt
            answer: The answer to validate
            
        Returns:
            Tuple of (valid, errors)
        """
        validator_method = getattr(self, f'_validate_{category}', None)
        if validator_method:
            return validator_method(prompt, answer)
        else:
            # Default validation for unknown categories
            return self._validate_default(prompt, answer)
    
    def _validate_factual_knowledge(self, prompt: str, answer: str) -> Tuple[bool, list]:
        """Validate factual knowledge answer."""
        errors = []
        
        # Check non-empty
        if not answer or not answer.strip():
            errors.append("Answer is empty")
            return False, errors
        
        # Check directly addresses prompt
        # This is hard to validate automatically, but we can do basic checks
        prompt_lower = prompt.lower()
        answer_lower = answer.lower()
        
        # Check for obvious refusals
        refusal_patterns = [
            "i don't know",
            "i cannot",
            "i'm sorry",
            "unable to",
            "not possible",
            "refuse to",
            "cannot answer"
        ]
        
        for pattern in refusal_patterns:
            if pattern in answer_lower:
                errors.append(f"Answer contains refusal: '{pattern}'")
        
        # Check requested format if specified
        # Look for format hints in the prompt
        if 'list' in prompt_lower or 'enumerate' in prompt_lower:
            if not any(c in answer for c in [',', ';', '\n', '-', '*', '1.', 'A)']):
                errors.append("Expected list format but answer is not formatted as a list")
        
        return len(errors) == 0, errors
    
    def _validate_mathematical_reasoning(self, prompt: str, answer: str) -> Tuple[bool, list]:
        """Validate mathematical reasoning answer."""
        errors = []
        
        # Check non-empty
        if not answer or not answer.strip():
            errors.append("Answer is empty")
            return False, errors
        
        # Check numeric form
        answer_stripped = answer.strip()
        
        # Try to extract numeric value
        numeric_pattern = r'[-+]?\d+\.?\d*'
        numbers = re.findall(numeric_pattern, answer_stripped)
        
        if not numbers:
            errors.append("Answer does not contain a numeric value")
        
        # Check if we can recompute
        try:
            # Extract mathematical expression from prompt
            expr_matches = re.findall(r'[\d]+[\s]*[+\-*/%^**][\s]*[\d]+', prompt)
            if expr_matches:
                # Try to evaluate the expression
                expected = arithmetic_evaluator.evaluate(expr_matches[0])
                
                # Try to parse the answer as a number
                if numbers:
                    answer_num = float(numbers[0])
                    # Check if close to expected (with some tolerance)
                    if abs(answer_num - expected) > 0.001:
                        errors.append(f"Answer {answer_num} != expected {expected}")
        except:
            pass  # Recomputation failed, not an error
        
        # Check for units if present in prompt
        units = re.findall(r'\b(percent|percentage|%|\$|€|£|kg|g|m|cm|km|hours?|mins?|secs?)\b', prompt, re.IGNORECASE)
        if units:
            # Check if answer includes units
            if not any(unit.lower() in answer_lower for unit in units):
                errors.append(f"Expected units ({units}) in answer")
        
        return len(errors) == 0, errors
    
    def _validate_sentiment_classification(self, prompt: str, answer: str) -> Tuple[bool, list]:
        """Validate sentiment classification answer."""
        errors = []
        
        # Check allowed label
        valid, label, error = sentiment_validator.validate_sentiment_output(answer)
        if not valid:
            errors.append(error or "Invalid sentiment label")
            return False, errors
        
        # Check exact format
        answer_lower = answer.lower().strip()
        allowed_labels = ['positive', 'negative', 'neutral']
        
        if answer_lower not in allowed_labels:
            errors.append(f"Label must be one of: {allowed_labels}")
            return False, errors
        
        # Check for extra text
        if len(answer.split()) > 1:
            # Might have justification, which is OK if requested
            if 'justification' not in prompt.lower() and 'explain' not in prompt.lower():
                errors.append("Extra text detected; only the label should be returned")
        
        return len(errors) == 0, errors
    
    def _validate_text_summarisation(self, prompt: str, answer: str) -> Tuple[bool, list]:
        """Validate text summarization answer."""
        errors = []
        
        # Check non-empty
        if not answer or not answer.strip():
            errors.append("Summary is empty")
            return False, errors
        
        # Check if it's a copy of the source
        if summary_checker.is_copy_of_source(answer, prompt):
            errors.append("Summary is essentially a copy of the source text")
        
        # Check word count limits if specified
        word_match = re.search(r'(\d+)\s+words?', prompt, re.IGNORECASE)
        if word_match:
            max_words = int(word_match.group(1))
            word_count = summary_checker.count_words(answer)
            if word_count > max_words:
                errors.append(f"Word count {word_count} exceeds limit {max_words}")
        
        # Check sentence count limits if specified
        sentence_match = re.search(r'(\d+)\s+sentences?', prompt, re.IGNORECASE)
        if sentence_match:
            max_sentences = int(sentence_match.group(1))
            sentence_count = summary_checker.count_sentences(answer)
            if sentence_count > max_sentences:
                errors.append(f"Sentence count {sentence_count} exceeds limit {max_sentences}")
        
        # Check boundedness
        bounded, bounded_error = summary_checker.check_boundedness(answer, prompt)
        if not bounded:
            errors.append(bounded_error)
        
        return len(errors) == 0, errors
    
    def _validate_named_entity_recognition(self, prompt: str, answer: str) -> Tuple[bool, list]:
        """Validate named entity recognition answer."""
        errors = []
        
        # Check non-empty
        if not answer or not answer.strip():
            errors.append("Entity extraction is empty")
            return False, errors
        
        # Try to validate as JSON
        valid, entities, error = ner_validator.validate_ner_output(answer, prompt)
        if not valid:
            errors.append(error or "Invalid NER output format")
            return False, errors
        
        # Check allowed entity labels
        for entity in entities:
            entity_type = entity.get('type', '')
            if entity_type not in ner_validator.SUPPORTED_TYPES:
                errors.append(f"Unsupported entity type: {entity_type}")
        
        # Check for required fields
        for entity in entities:
            if 'value' not in entity and 'entity' not in entity:
                errors.append("Entity missing 'value' or 'entity' field")
            if 'type' not in entity:
                errors.append("Entity missing 'type' field")
        
        # Check for duplicates
        seen = set()
        for entity in entities:
            key = (entity.get('type'), entity.get('value'))
            if key in seen:
                errors.append(f"Duplicate entity: {key}")
            seen.add(key)
        
        return len(errors) == 0, errors
    
    def _validate_code_debugging(self, prompt: str, answer: str) -> Tuple[bool, list]:
        """Validate code debugging answer."""
        errors = []
        
        # Check non-empty
        if not answer or not answer.strip():
            errors.append("Code is empty")
            return False, errors
        
        # Extract code from answer
        codes = code_checker.extract_code_from_text(answer)
        if not codes:
            errors.append("No code found in answer")
            return False, errors
        
        # Check syntax
        for code in codes:
            valid, error = code_checker.check_syntax(code)
            if not valid:
                errors.append(f"Syntax error: {error}")
        
        # Check if explanation is required but missing
        if 'explain' in prompt.lower() or 'why' in prompt.lower():
            # Should have explanation
            if len(answer.split('\n')) < 2 and len(answer) < 100:
                errors.append("Expected explanation but answer is too short")
        
        return len(errors) == 0, errors
    
    def _validate_logical_reasoning(self, prompt: str, answer: str) -> Tuple[bool, list]:
        """Validate logical reasoning answer."""
        errors = []
        
        # Check non-empty
        if not answer or not answer.strip():
            errors.append("Answer is empty")
            return False, errors
        
        # Validate multiple choice
        candidates = logic_checker.extract_candidates(prompt)
        if candidates:
            valid, error = logic_checker.validate_multiple_choice(prompt, answer)
            if not valid:
                errors.append(error)
        
        # Check for contradictions
        constraints = logic_checker._extract_constraints(prompt)
        contradictions = logic_checker.detect_contradictions(answer, constraints)
        errors.extend(contradictions)
        
        return len(errors) == 0, errors
    
    def _validate_code_generation(self, prompt: str, answer: str) -> Tuple[bool, list]:
        """Validate code generation answer."""
        errors = []
        
        # Check non-empty
        if not answer or not answer.strip():
            errors.append("Code is empty")
            return False, errors
        
        # Extract code from answer
        codes = code_checker.extract_code_from_text(answer)
        if not codes:
            errors.append("No code found in answer")
            return False, errors
        
        # Check syntax for each code block
        for code in codes:
            valid, error = code_checker.check_syntax(code)
            if not valid:
                errors.append(f"Syntax error in code: {error}")
        
        # Check for forbidden extra output
        # If the prompt asks for only code, check that there's not too much extra text
        prompt_lower = prompt.lower()
        if 'only code' in prompt_lower or 'return only the code' in prompt_lower:
            # Calculate ratio of code to total answer
            code_length = sum(len(c) for c in codes)
            total_length = len(answer)
            code_ratio = code_length / total_length if total_length > 0 else 0
            
            if code_ratio < 0.7:  # Less than 70% is code
                errors.append("Too much non-code text; expected only code")
        
        # Check signature if specified
        # Look for function name in prompt
        func_name = None
        
        # Check for "def func_name(" pattern
        match = re.search(r'def\s+(\w+)\s*\(', prompt)
        if match:
            func_name = match.group(1)
        else:
            # Check for "called my_func" or "named my_func" or "write a function my_func" patterns
            # Only match if the word after is a plausible function name (not common English words)
            common_words = {'to', 'that', 'the', 'a', 'an', 'for', 'which', 'this', 'of', 'in', 'is'}
            match = re.search(r'(?:called|named|write\s+(?:a\s+)?function)\s+[\"\']?(\w+)[\"\']?', prompt, re.IGNORECASE)
            if match:
                func_name = match.group(1)
                # Don't use it if it's a common word
                if func_name.lower() in common_words:
                    func_name = None
        
        if func_name:
            # Check if function name is in the answer
            if func_name not in answer:
                errors.append(f"Expected function '{func_name}' not found in answer")
        
        return len(errors) == 0, errors
    
    def _validate_default(self, prompt: str, answer: str) -> Tuple[bool, list]:
        """Default validation for unknown categories."""
        errors = []
        
        if not answer or not answer.strip():
            errors.append("Answer is empty")
        
        return len(errors) == 0, errors


# Singleton instance
_category_validator_instance = None

def get_category_validator() -> CategoryValidator:
    """Get or create the singleton category validator instance."""
    global _category_validator_instance
    if _category_validator_instance is None:
        _category_validator_instance = CategoryValidator()
    return _category_validator_instance
