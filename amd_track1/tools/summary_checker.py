"""
Tool 4: Summary Constraint Checker

Validates summary outputs against word/sentence limits and other constraints.
"""

import re
from typing import Optional, Tuple


class SummaryConstraintChecker:
    """Summary constraint validator."""
    
    SENTENCE_PATTERN = re.compile(r'[.!?]+')
    WORD_PATTERN = re.compile(r'\S+')
    
    def count_sentences(self, text: str) -> int:
        """Count the number of sentences in text."""
        if not text.strip():
            return 0
        # Split by sentence terminators
        sentences = self.SENTENCE_PATTERN.split(text)
        # Filter out empty strings
        sentences = [s.strip() for s in sentences if s.strip()]
        return len(sentences)
    
    def count_words(self, text: str) -> int:
        """Count the number of words in text."""
        words = self.WORD_PATTERN.findall(text)
        return len(words)
    
    def is_empty_or_whitespace(self, text: str) -> bool:
        """Check if text is empty or only whitespace."""
        return not text.strip()
    
    def is_copy_of_source(self, summary: str, source: str, threshold: float = 0.95) -> bool:
        """
        Check if summary is essentially a copy of the source.
        
        Uses a simple similarity check based on shared words.
        
        Args:
            summary: The summary text
            source: The source text
            threshold: Similarity threshold (0-1)
            
        Returns:
            True if summary is too similar to source
        """
        if not summary.strip() or not source.strip():
            return False
        
        summary_words = set(self.WORD_PATTERN.findall(summary.lower()))
        source_words = set(self.WORD_PATTERN.findall(source.lower()))
        
        if not source_words:
            return False
        
        intersection = summary_words & source_words
        similarity = len(intersection) / len(source_words)
        
        return similarity >= threshold
    
    def check_length_constraints(self, summary: str, 
                                  max_words: Optional[int] = None,
                                  max_sentences: Optional[int] = None,
                                  min_words: Optional[int] = None) -> Tuple[bool, list]:
        """
        Check summary length constraints.
        
        Args:
            summary: The summary text
            max_words: Maximum allowed words
            max_sentences: Maximum allowed sentences
            min_words: Minimum required words
            
        Returns:
            Tuple of (passes, violations)
        """
        violations = []
        
        if self.is_empty_or_whitespace(summary):
            violations.append("Summary is empty or whitespace only")
            return False, violations
        
        word_count = self.count_words(summary)
        sentence_count = self.count_sentences(summary)
        
        if max_words is not None and word_count > max_words:
            violations.append(f"Word count {word_count} exceeds maximum {max_words}")
        
        if max_sentences is not None and sentence_count > max_sentences:
            violations.append(f"Sentence count {sentence_count} exceeds maximum {max_sentences}")
        
        if min_words is not None and word_count < min_words:
            violations.append(f"Word count {word_count} is below minimum {min_words}")
        
        return len(violations) == 0, violations
    
    def validate_format(self, summary: str, expected_format: str) -> Tuple[bool, str]:
        """
        Validate summary format.
        
        Args:
            summary: The summary text
            expected_format: One of 'text', 'bullet_points', 'numbered_list', 'paragraph'
            
        Returns:
            Tuple of (valid, error_message)
        """
        if not summary.strip():
            return False, "Summary is empty"
        
        if expected_format == 'bullet_points':
            lines = [l.strip() for l in summary.split('\n') if l.strip()]
            if not lines:
                return False, "No content"
            # Check if most lines start with bullet point markers
            bullet_lines = sum(1 for l in lines if l.startswith(('- ', '* ', '+ ')))
            if bullet_lines < len(lines):
                return False, f"Not all lines are bullet points ({bullet_lines}/{len(lines)})"
        
        elif expected_format == 'numbered_list':
            lines = [l.strip() for l in summary.split('\n') if l.strip()]
            if not lines:
                return False, "No content"
            # Check if lines are numbered
            for i, line in enumerate(lines):
                if not re.match(r'^\d+[\.\)]\s', line):
                    return False, f"Line {i+1} is not properly numbered"
        
        elif expected_format == 'paragraph':
            # Should be a single paragraph (no newlines or at most one)
            if '\n' in summary.strip() and summary.strip().count('\n') > 1:
                return False, "Multiple paragraphs detected"
        
        return True, ""
    
    def check_boundedness(self, summary: str, source: str) -> Tuple[bool, str]:
        """
        Check if summary stays within the bounds of the source.
        
        Args:
            summary: The summary text
            source: The source text
            
        Returns:
            Tuple of (bounded, error_message)
        """
        if not summary.strip():
            return False, "Summary is empty"
        
        if not source.strip():
            return False, "Cannot validate boundedness without source"
        
        # Check if summary is a copy
        if self.is_copy_of_source(summary, source):
            return False, "Summary is essentially a copy of the source"
        
        # Check if summary introduces new concepts not in source
        # This is a simplified check - for full validation, model should be used
        summary_words = set(self.WORD_PATTERN.findall(summary.lower()))
        source_words = set(self.WORD_PATTERN.findall(source.lower()))
        
        new_words = summary_words - source_words
        # Remove common stop words that might be added
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with'}
        new_words = new_words - stop_words
        
        # Allow some new words (from rephrasing)
        if len(new_words) > len(summary_words) * 0.3:  # More than 30% new words
            return False, f"Summary introduces too many new concepts: {new_words}"
        
        return True, ""
    
    def validate_summary(self, summary: str, source: str,
                         max_words: Optional[int] = None,
                         max_sentences: Optional[int] = None,
                         expected_format: Optional[str] = None) -> Tuple[bool, list]:
        """
        Comprehensive summary validation.
        
        Args:
            summary: The summary to validate
            source: The source text
            max_words: Maximum word count
            max_sentences: Maximum sentence count
            expected_format: Expected format string
            
        Returns:
            Tuple of (valid, violations)
        """
        violations = []
        
        # Check empty
        if self.is_empty_or_whitespace(summary):
            violations.append("Summary is empty or whitespace")
            return False, violations
        
        # Check length constraints
        length_valid, length_violations = self.check_length_constraints(
            summary, max_words=max_words, max_sentences=max_sentences
        )
        violations.extend(length_violations)
        
        # Check format
        if expected_format:
            format_valid, format_error = self.validate_format(summary, expected_format)
            if not format_valid:
                violations.append(format_error)
        
        # Check boundedness
        bounded, bounded_error = self.check_boundedness(summary, source)
        if not bounded:
            violations.append(bounded_error)
        
        return len(violations) == 0, violations


# Singleton instance
summary_checker = SummaryConstraintChecker()
