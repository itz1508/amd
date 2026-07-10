"""
Tool 2: JSON Validator and Repair Detector

Validates JSON structure, checks required fields, type checks,
and detects markdown fences. Does not perform semantic rewriting.
"""

import json
import re
from typing import Any, Optional, Tuple


class JSONValidator:
    """JSON structure validator."""
    
    MARKDOWN_FENCE_PATTERN = re.compile(r'```(?:json)?([\s\S]*?)```', re.IGNORECASE)
    
    def parse(self, json_str: str) -> Tuple[bool, Optional[dict], Optional[str]]:
        """
        Parse and validate JSON string.
        
        Args:
            json_str: The string to parse
            
        Returns:
            Tuple of (success, parsed_data, error_message)
        """
        try:
            data = json.loads(json_str)
            return True, data, None
        except json.JSONDecodeError as e:
            return False, None, str(e)
    
    def validate_array(self, data: Any) -> bool:
        """Check if data is a JSON array (list)."""
        return isinstance(data, list)
    
    def validate_object(self, data: Any) -> bool:
        """Check if data is a JSON object (dict)."""
        return isinstance(data, dict)
    
    def check_required_fields(self, data: dict, required_fields: list) -> Tuple[bool, list]:
        """
        Check if all required fields are present.
        
        Args:
            data: The dictionary to check
            required_fields: List of field names that must be present
            
        Returns:
            Tuple of (all_present, missing_fields)
        """
        missing = [f for f in required_fields if f not in data]
        return len(missing) == 0, missing
    
    def check_types(self, data: dict, type_spec: dict) -> Tuple[bool, dict]:
        """
        Check if fields have the correct types.
        
        Args:
            data: The dictionary to check
            type_spec: Dict mapping field names to expected types
                      e.g., {"task_id": str, "prompt": str}
            
        Returns:
            Tuple of (all_correct, type_errors)
        """
        errors = {}
        for field, expected_type in type_spec.items():
            if field in data:
                if not isinstance(data[field], expected_type):
                    actual_type = type(data[field]).__name__
                    errors[field] = f"Expected {expected_type.__name__}, got {actual_type}"
        return len(errors) == 0, errors
    
    def validate_tasks_json(self, json_str: str) -> Tuple[bool, Optional[list], Optional[str]]:
        """
        Validate that the input is a proper tasks.json structure.
        
        Checks:
        - Root is a JSON array
        - Every item is an object
        - Every task has task_id and prompt
        - Task IDs are unique
        
        Args:
            json_str: The JSON string to validate
            
        Returns:
            Tuple of (valid, tasks_list_or_none, error_message)
        """
        success, data, error = self.parse(json_str)
        if not success:
            return False, None, f"Invalid JSON: {error}"
        
        if not self.validate_array(data):
            return False, None, "Root must be a JSON array"
        
        seen_ids = set()
        for i, item in enumerate(data):
            if not self.validate_object(item):
                return False, None, f"Item {i} is not an object"
            
            # Check required fields
            has_task_id = 'task_id' in item and isinstance(item['task_id'], str) and len(item['task_id'].strip()) > 0
            has_prompt = 'prompt' in item and isinstance(item['prompt'], str) and len(item['prompt'].strip()) > 0
            
            if not has_task_id:
                return False, None, f"Item {i} missing or invalid task_id"
            if not has_prompt:
                return False, None, f"Item {i} missing or invalid prompt"
            
            # Check for duplicate IDs
            if item['task_id'] in seen_ids:
                return False, None, f"Duplicate task_id: {item['task_id']}"
            seen_ids.add(item['task_id'])
        
        return True, data, None
    
    def detect_markdown_fences(self, text: str) -> list:
        """
        Detect JSON markdown fences in text.
        
        Args:
            text: Text to search
            
        Returns:
            List of JSON strings found within markdown fences
        """
        matches = self.MARKDOWN_FENCE_PATTERN.findall(text)
        results = []
        for match in matches:
            stripped = match.strip()
            if stripped:
                results.append(stripped)
        return results
    
    def extract_json_from_text(self, text: str) -> Optional[dict]:
        """
        Try to extract and parse JSON from text (e.g., from markdown fences).
        
        Args:
            text: Text that may contain JSON
            
        Returns:
            Parsed JSON dict if found, None otherwise
        """
        # Try to detect markdown fenced JSON
        fences = self.detect_markdown_fences(text)
        for fence in fences:
            success, data, _ = self.parse(fence)
            if success and self.validate_object(data):
                return data
        
        # Try to parse the whole text as JSON
        success, data, _ = self.parse(text)
        if success and self.validate_object(data):
            return data
        
        return None
    
    def repair_detector(self, original: str, repaired: str) -> bool:
        """
        Detect if a string has been repaired (changed) from original.
        
        Args:
            original: Original JSON string
            repaired: Potentially repaired JSON string
            
        Returns:
            True if the JSON was changed/repaired
        """
        if original == repaired:
            return False
        
        # Both must be valid JSON
        orig_valid, orig_data, _ = self.parse(original)
        repa_valid, repa_data, _ = self.parse(repaired)
        
        if not orig_valid and repa_valid:
            return True
        if orig_valid and repa_valid and orig_data != repa_data:
            return True
        
        return False


# Singleton instance
json_validator = JSONValidator()
