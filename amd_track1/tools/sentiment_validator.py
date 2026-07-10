"""
Tool 3: Sentiment Label Validator

Validates sentiment classification outputs against allowed labels.
"""

from typing import Optional, Tuple, Union
import json


class SentimentValidator:
    """Sentiment label validator."""
    
    # Allowed sentiment labels
    ALLOWED_LABELS = {'positive', 'negative', 'neutral'}
    
    # Alternative label mappings (normalize to standard)
    LABEL_MAPPINGS = {
        'pos': 'positive',
        'neg': 'negative',
        'neutral': 'neutral',
        'positive': 'positive',
        'negative': 'negative',
        'happy': 'positive',
        'sad': 'negative',
        'angry': 'negative',
        'good': 'positive',
        'bad': 'negative',
    }
    
    def normalize_label(self, label: str) -> Optional[str]:
        """
        Normalize a sentiment label to one of the allowed labels.
        
        Args:
            label: The label to normalize
            
        Returns:
            Normalized label or None if not mappable
        """
        label_lower = label.lower().strip()
        return self.LABEL_MAPPINGS.get(label_lower)
    
    def is_allowed_label(self, label: str) -> bool:
        """
        Check if a label is in the allowed set.
        
        Args:
            label: The label to check
            
        Returns:
            True if allowed
        """
        normalized = self.normalize_label(label)
        return normalized in self.ALLOWED_LABELS
    
    def validate_sentiment_output(self, output: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate a sentiment classification output.
        
        Args:
            output: The sentiment output string
            
        Returns:
            Tuple of (valid, normalized_label, error_message)
        """
        # Strip and normalize
        label = output.strip()
        
        # Check if it's valid JSON with a sentiment field
        if label.startswith('{') and label.endswith('}'):
            try:
                data = json.loads(label)
                if 'sentiment' in data:
                    label = data['sentiment']
                elif 'label' in data:
                    label = data['label']
            except:
                pass
        
        normalized = self.normalize_label(label)
        
        if normalized is None:
            return False, None, f"Label '{label}' is not a recognized sentiment label"
        
        if normalized not in self.ALLOWED_LABELS:
            return False, None, f"Label '{label}' maps to '{normalized}' which is not allowed"
        
        return True, normalized, None
    
    def validate_with_justification(self, output: str, require_justification: bool = False) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
        """
        Validate sentiment output that may include justification.
        
        Args:
            output: The output string
            require_justification: Whether justification is required
            
        Returns:
            Tuple of (valid, normalized_label, justification, error_message)
        """
        # Try to parse as JSON first
        if output.startswith('{') and output.endswith('}'):
            try:
                data = json.loads(output)
                label = data.get('sentiment', data.get('label', ''))
                justification = data.get('justification', data.get('reason', data.get('explanation', None)))
                
                normalized = self.normalize_label(label)
                if normalized is None:
                    return False, None, None, f"Invalid sentiment label: {label}"
                
                if normalized not in self.ALLOWED_LABELS:
                    return False, None, None, f"Label '{label}' is not allowed"
                
                if require_justification and not justification:
                    return False, None, None, "Justification is required but missing"
                
                return True, normalized, justification, None
            except:
                pass
        
        # Treat as plain text
        # Check if it's just a label
        label = output.strip()
        normalized = self.normalize_label(label)
        
        if normalized is None or normalized not in self.ALLOWED_LABELS:
            return False, None, None, f"Invalid sentiment label: {label}"
        
        if require_justification:
            return False, None, None, "Justification is required but output is label only"
        
        return True, normalized, None, None
    
    def extract_label_from_text(self, text: str) -> Optional[str]:
        """
        Try to extract a sentiment label from arbitrary text.
        
        Looks for patterns like "sentiment: positive" or just "positive".
        
        Args:
            text: Text that may contain a sentiment label
            
        Returns:
            Extracted normalized label or None
        """
        # Check for explicit patterns
        for prefix in ['sentiment:', 'label:', 'tone:']:
            if prefix in text.lower():
                parts = text.split(prefix, 1)[1].split()
                if parts:
                    label = parts[0].strip().rstrip(':').strip()
                    normalized = self.normalize_label(label)
                    if normalized:
                        return normalized
        
        # Check if the whole text is just a label
        normalized = self.normalize_label(text)
        if normalized:
            return normalized
        
        return None
    
    def check_unsupported_labels(self, output: str) -> list:
        """
        Detect any unsupported labels in the output.
        
        Args:
            output: The output to check
            
        Returns:
            List of unsupported labels found
        """
        # Extract all words that might be labels
        words = output.split()
        unsupported = []
        
        for word in words:
            # Clean the word
            cleaned = word.strip('.,:;"\'()[]{}').lower()
            normalized = self.normalize_label(cleaned)
            
            # If it normalizes to something but that's not in allowed labels
            if normalized and cleaned not in self.LABEL_MAPPINGS.values():
                # This shouldn't happen with our current mappings, but check anyway
                if normalized not in self.ALLOWED_LABELS:
                    unsupported.append(word)
        
        return unsupported


# Singleton instance
sentiment_validator = SentimentValidator()
