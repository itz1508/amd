"""
Tool 5: Named-Entity Output Validator

Validates named entity recognition outputs.
"""

import json
import re
from typing import Any, Optional, Tuple, Union


class NamedEntityValidator:
    """Named entity output validator."""
    
    # Supported entity types
    SUPPORTED_TYPES = {'person', 'organization', 'location', 'date'}
    
    # Patterns for detecting entities in text
    ENTITY_PATTERNS = {
        'date': re.compile(
            r'\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b|'  # YYYY-MM-DD or YYYY/MM/DD
            r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b|'  # MM/DD/YYYY or DD/MM/YYYY
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b|'  # Month Day, Year
            r'\b(?:January|February|March|April|May|June|July|August|September|'
            r'October|November|December)\s+\d{1,2},?\s+\d{4}\b'
        ),
    }
    
    def validate_entity_type(self, entity_type: str) -> bool:
        """
        Check if an entity type is supported.
        
        Args:
            entity_type: The type to validate
            
        Returns:
            True if supported
        """
        return entity_type.lower() in self.SUPPORTED_TYPES
    
    def validate_json_output(self, output: str) -> Tuple[bool, list, str]:
        """
        Validate JSON-formatted NER output.
        
        Expected format:
        [
          {"type": "person", "value": "John Doe"},
          {"type": "organization", "value": "ACME Corp"}
        ]
        
        Args:
            output: The JSON string to validate
            
        Returns:
            Tuple of (valid, entities, error_message)
        """
        try:
            data = json.loads(output)
        except json.JSONDecodeError as e:
            return False, [], f"Invalid JSON: {e}"
        
        if not isinstance(data, list):
            return False, [], "Expected JSON array"
        
        entities = []
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                return False, [], f"Item {i} is not an object"
            
            # Check required fields
            if 'type' not in item:
                return False, [], f"Item {i} missing 'type' field"
            if 'value' not in item and 'entity' not in item:
                return False, [], f"Item {i} missing 'value' or 'entity' field"
            
            entity_type = item.get('type', '').lower()
            if not self.validate_entity_type(entity_type):
                return False, [], f"Item {i} has unsupported type: {entity_type}"
            
            entity_value = item.get('value', item.get('entity', ''))
            if not entity_value or not isinstance(entity_value, str):
                return False, [], f"Item {i} has invalid value"
            
            # Check for span if present
            if 'span' in item:
                span = item['span']
                if not isinstance(span, (list, tuple)) or len(span) != 2:
                    return False, [], f"Item {i} has invalid span format"
            
            entities.append({
                'type': entity_type,
                'value': entity_value,
                'span': item.get('span')
            })
        
        # Check for duplicates
        seen = set()
        for e in entities:
            key = (e['type'], e['value'])
            if key in seen:
                return False, [], f"Duplicate entity: {e}"
            seen.add(key)
        
        return True, entities, ""
    
    def validate_text_output(self, output: str, text: Optional[str] = None) -> Tuple[bool, list, str]:
        """
        Validate text-formatted NER output.
        
        Expected format:
        person: John Doe
        organization: ACME Corp
        location: New York
        
        Args:
            output: The text output to validate
            text: Optional source text for span validation
            
        Returns:
            Tuple of (valid, entities, error_message)
        """
        entities = []
        lines = output.strip().split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Parse "type: value" format
            if ':' not in line:
                return False, [], f"Line {i+1} missing colon separator"
            
            parts = line.split(':', 1)
            entity_type = parts[0].strip().lower()
            entity_value = parts[1].strip()
            
            if not entity_type or not entity_value:
                return False, [], f"Line {i+1} has empty type or value"
            
            if not self.validate_entity_type(entity_type):
                return False, [], f"Line {i+1} has unsupported type: {entity_type}"
            
            entities.append({
                'type': entity_type,
                'value': entity_value,
                'span': None
            })
        
        # Check for duplicates
        seen = set()
        for e in entities:
            key = (e['type'], e['value'])
            if key in seen:
                return False, [], f"Duplicate entity: {e}"
            seen.add(key)
        
        return True, entities, ""
    
    def validate_ner_output(self, output: str, source_text: Optional[str] = None) -> Tuple[bool, list, str]:
        """
        Validate NER output in any supported format.
        
        Args:
            output: The output to validate
            source_text: Optional source text for additional validation
            
        Returns:
            Tuple of (valid, entities, error_message)
        """
        if not output.strip():
            return False, [], "Empty output"
        
        # Try JSON first
        if output.strip().startswith('[') or output.strip().startswith('{'):
            return self.validate_json_output(output)
        
        # Try text format
        return self.validate_text_output(output, source_text)
    
    def check_required_fields(self, entities: list, required_types: Optional[list] = None) -> Tuple[bool, list]:
        """
        Check if all required entity types are present.
        
        Args:
            entities: List of extracted entities
            required_types: List of types that must be present
            
        Returns:
            Tuple of (all_present, missing_types)
        """
        if not required_types:
            return True, []
        
        present_types = {e['type'] for e in entities}
        missing = [t for t in required_types if t.lower() not in present_types]
        return len(missing) == 0, missing
    
    def extract_entities_from_text(self, text: str) -> list:
        """
        Simple entity extraction from text (for validation purposes only).
        
        This is a basic extractor - the model should do the actual extraction.
        
        Args:
            text: Text to extract entities from
            
        Returns:
            List of potential entities with types
        """
        entities = []
        
        # Extract dates
        for match in self.ENTITY_PATTERNS['date'].finditer(text):
            entities.append({
                'type': 'date',
                'value': match.group(),
                'span': [match.start(), match.end()]
            })
        
        # For other types, we'd need more sophisticated NLP
        # This is just a placeholder for validation
        
        return entities
    
    def validate_spans(self, entities: list, source_text: str) -> Tuple[bool, list]:
        """
        Validate that entity spans are correct.
        
        Args:
            entities: List of entities with spans
            source_text: The source text
            
        Returns:
            Tuple of (all_valid, errors)
        """
        errors = []
        
        for i, entity in enumerate(entities):
            if 'span' not in entity or entity['span'] is None:
                continue
            
            span = entity['span']
            if len(span) != 2:
                errors.append(f"Entity {i} has invalid span")
                continue
            
            start, end = span
            if start < 0 or end > len(source_text):
                errors.append(f"Entity {i} span [{start}:{end}] out of bounds for text of length {len(source_text)}")
                continue
            
            extracted = source_text[start:end]
            if extracted != entity['value']:
                errors.append(f"Entity {i} span [{start}:{end}] '{extracted}' != '{entity['value']}'")
        
        return len(errors) == 0, errors


# Singleton instance
ner_validator = NamedEntityValidator()
