"""
Tool 7: Logic Consistency Checker

Validates logical reasoning outputs for consistency.
"""

import json
import re
from typing import Optional, Tuple


class LogicConsistencyChecker:
    """Logic consistency validator."""
    
    def extract_candidates(self, text: str) -> list:
        """
        Extract candidate choices from text.
        
        Looks for patterns like:
        - A) Option 1
        - 1. Option 1
        - - Option 1
        - * Option 1
        
        Args:
            text: Text containing choices
            
        Returns:
            List of candidate strings
        """
        candidates = []
        lines = text.split('\n')
        
        # Pattern for letter-numbered options: A) text, B) text, etc.
        letter_pattern = re.compile(r'^\s*[A-Za-z]\)\s+(.+)$')
        # Pattern for number options: 1. text, 2. text, etc.
        number_pattern = re.compile(r'^\s*\d+[\.\)]\s+(.+)$')
        # Pattern for bullet points: - text, * text, + text
        bullet_pattern = re.compile(r'^\s*[-*+]\s+(.+)$')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            match = letter_pattern.match(line)
            if match:
                candidates.append(match.group(1).strip())
                continue
            
            match = number_pattern.match(line)
            if match:
                candidates.append(match.group(1).strip())
                continue
            
            match = bullet_pattern.match(line)
            if match:
                candidates.append(match.group(1).strip())
                continue
            
            # If line looks like an option but doesn't match patterns
            # (e.g., just a word or phrase)
            if len(line.split()) <= 5 and line not in ['Options:', 'Choose:', 'Select:']:
                candidates.append(line)
        
        return candidates
    
    def check_exact_one_answer(self, answer: str, candidates: list) -> bool:
        """
        Check if answer selects exactly one candidate.
        
        Args:
            answer: The selected answer
            candidates: List of valid candidates
            
        Returns:
            True if exactly one candidate is selected
        """
        if not candidates:
            return True  # No candidates to check against
        
        # Count how many candidates are in the answer
        count = 0
        for candidate in candidates:
            if candidate in answer:
                count += 1
        
        return count == 1
    
    def detect_contradictions(self, answer: str, constraints: Optional[list] = None) -> list:
        """
        Detect contradictions in the answer based on known constraints.
        
        Args:
            answer: The answer to check
            constraints: Optional list of constraints to check against
            
        Returns:
            List of detected contradictions
        """
        contradictions = []
        
        if not constraints:
            return contradictions
        
        answer_lower = answer.lower()
        
        for constraint in constraints:
            constraint_lower = constraint.lower()
            
            # Check for direct contradictions
            if 'not' in constraint_lower or 'cannot' in constraint_lower:
                # Extract the forbidden item
                # This is simplified - full NLP would be needed for robust detection
                pass
            
            # Check for mutual exclusivity
            # e.g., "A and B cannot both be true"
            if ' and ' in constraint_lower and 'cannot both' in constraint_lower:
                parts = constraint_lower.split(' and ')
                if len(parts) == 2:
                    item1 = parts[0].replace('cannot both', '').strip()
                    item2 = parts[1].strip()
                    
                    if item1 in answer_lower and item2 in answer_lower:
                        contradictions.append(f"Both '{item1}' and '{item2}' cannot be true")
        
        return contradictions
    
    def check_deterministic_enumeration(self, prompt: str, answer: str) -> Tuple[bool, Optional[list]]:
        """
        Check if a small bounded puzzle can be solved by enumeration.
        
        For problems with a small number of possibilities, we can check
        if the answer is one of the valid possibilities.
        
        Args:
            prompt: The original problem/prompt
            answer: The provided answer
            
        Returns:
            Tuple of (can_verify, valid_answers_or_none)
        """
        # Extract candidates from prompt
        candidates = self.extract_candidates(prompt)
        
        if len(candidates) <= 20:  # Small enough for enumeration
            return True, candidates
        
        return False, None
    
    def validate_logic_answer(self, prompt: str, answer: str) -> Tuple[bool, list]:
        """
        Validate a logic/reasoning answer.
        
        Args:
            prompt: The original problem
            answer: The answer to validate
            
        Returns:
            Tuple of (valid, errors)
        """
        errors = []
        
        # Extract candidates from prompt
        candidates = self.extract_candidates(prompt)
        
        # If there are candidates, check that answer selects exactly one
        if candidates:
            if not self.check_exact_one_answer(answer, candidates):
                errors.append(f"Answer must select exactly one of the {len(candidates)} options")
        
        # Try to detect contradictions
        # Extract constraints from prompt
        constraints = self._extract_constraints(prompt)
        contradictions = self.detect_contradictions(answer, constraints)
        errors.extend(contradictions)
        
        return len(errors) == 0, errors
    
    def _extract_constraints(self, text: str) -> list:
        """
        Extract explicit constraints from text.
        
        Args:
            text: Text containing constraints
            
        Returns:
            List of constraint strings
        """
        constraints = []
        lines = text.split('\n')
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Look for constraint keywords
            constraint_keywords = [
                'cannot', 'must not', 'must', 'should', 'should not',
                'only', 'exactly', 'at least', 'at most', 'never',
                'always', 'if', 'then', 'implies'
            ]
            
            for keyword in constraint_keywords:
                if keyword in line_lower and line.strip():
                    constraints.append(line.strip())
                    break
        
        return constraints
    
    def check_multi_part_logic(self, answer: str, parts: list) -> Tuple[bool, list]:
        """
        Validate multi-part logic answers.
        
        Args:
            answer: The complete answer
            parts: List of expected parts/questions
            
        Returns:
            Tuple of (all_answered, errors)
        """
        errors = []
        
        for i, part in enumerate(parts):
            if part not in answer and part.lower() not in answer.lower():
                # Check if the part is addressed
                # This is simplified - would need better matching
                errors.append(f"Part {i+1} not addressed: {part}")
        
        return len(errors) == 0, errors
    
    def validate_multiple_choice(self, prompt: str, answer: str) -> Tuple[bool, str]:
        """
        Validate a multiple-choice answer.
        
        Args:
            prompt: The prompt with choices
            answer: The selected answer (letter or option text)
            
        Returns:
            Tuple of (valid, error_message)
        """
        candidates = self.extract_candidates(prompt)
        
        if not candidates:
            return True, ""  # No candidates to validate against
        
        # Check if answer is a valid letter choice
        if len(answer.strip()) == 1 and answer.upper() in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            letter_index = ord(answer.upper()) - ord('A')
            if letter_index < len(candidates):
                return True, ""
            else:
                return False, f"Choice '{answer}' exceeds number of options ({len(candidates)})"
        
        # Check if answer matches one of the candidates
        if answer.strip() in candidates:
            return True, ""
        
        # Check if answer is a number corresponding to a candidate
        try:
            choice_num = int(answer.strip())
            if 1 <= choice_num <= len(candidates):
                return True, ""
            else:
                return False, f"Choice number {choice_num} exceeds number of options ({len(candidates)})"
        except ValueError:
            pass
        
        return False, f"Answer '{answer}' is not one of the valid choices"


# Singleton instance
logic_checker = LogicConsistencyChecker()
