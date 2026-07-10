"""
Tests for Input Validation module.
"""

import pytest
import json
import tempfile
import os


class TestInputValidator:
    """Tests for InputValidator class."""
    
    def test_valid_batch(self, input_validation):
        """Test validation of a valid batch."""
        data = [
            {'task_id': 'task1', 'prompt': 'What is 2+2?'},
            {'task_id': 'task2', 'prompt': 'Who wrote Hamlet?'}
        ]
        
        valid, tasks, malformed = input_validation.validate(data)
        
        assert valid is True
        assert len(tasks) == 2
        assert len(malformed) == 0
        assert tasks[0]['task_id'] == 'task1'
        assert tasks[1]['task_id'] == 'task2'
    
    def test_empty_batch(self, input_validation):
        """Test validation of empty batch."""
        data = []
        
        valid, tasks, malformed = input_validation.validate(data)
        
        assert valid is True
        assert len(tasks) == 0
        assert len(malformed) == 0
    
    def test_duplicate_task_ids(self, input_validation):
        """Test detection of duplicate task IDs."""
        data = [
            {'task_id': 'task1', 'prompt': 'First task'},
            {'task_id': 'task1', 'prompt': 'Duplicate task ID'}
        ]
        
        valid, tasks, malformed = input_validation.validate(data)
        
        # Should have validation error for duplicates
        assert valid is False
        # But should still return unique tasks
        assert len(tasks) == 1
        assert tasks[0]['task_id'] == 'task1'
    
    def test_missing_task_id(self, input_validation):
        """Test detection of missing task_id."""
        data = [
            {'prompt': 'No task_id here'}
        ]
        
        valid, tasks, malformed = input_validation.validate(data)
        
        assert valid is False
        assert len(tasks) == 0
        assert len(malformed) == 1
        assert 'missing task_id' in malformed[0]['error'].lower()
    
    def test_missing_prompt(self, input_validation):
        """Test detection of missing prompt."""
        data = [
            {'task_id': 'task1'}
        ]
        
        valid, tasks, malformed = input_validation.validate(data)
        
        assert valid is False
        assert len(tasks) == 0
        assert len(malformed) == 1
        assert 'missing prompt' in malformed[0]['error'].lower()
    
    def test_empty_task_id(self, input_validation):
        """Test detection of empty task_id."""
        data = [
            {'task_id': '   ', 'prompt': 'Has empty task_id'}
        ]
        
        valid, tasks, malformed = input_validation.validate(data)
        
        assert valid is False
        assert len(malformed) == 1
    
    def test_empty_prompt(self, input_validation):
        """Test detection of empty prompt."""
        data = [
            {'task_id': 'task1', 'prompt': ''}
        ]
        
        valid, tasks, malformed = input_validation.validate(data)
        
        assert valid is False
        assert len(malformed) == 1
    
    def test_non_object_items(self, input_validation):
        """Test detection of non-object items."""
        data = [
            {'task_id': 'task1', 'prompt': 'Valid'},
            'not an object',
            123
        ]
        
        valid, tasks, malformed = input_validation.validate(data)
        
        assert valid is False
        assert len(tasks) == 1
        assert len(malformed) == 2
    
    def test_root_not_array(self, input_validation):
        """Test detection of non-array root."""
        data = {'task_id': 'task1', 'prompt': 'Not an array'}
        
        valid, tasks, malformed = input_validation.validate(data)
        
        assert valid is False
        assert len(tasks) == 0
        assert 'Root must be a JSON array' in input_validation.get_errors()
    
    def test_validate_from_file(self, input_validation):
        """Test validation from file."""
        data = [
            {'task_id': 'task1', 'prompt': 'Test prompt'}
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            temp_path = f.name
        
        try:
            valid, tasks, malformed, error = input_validation.validate_from_file(temp_path)
            
            assert valid is True
            assert len(tasks) == 1
            assert len(malformed) == 0
            assert error == ''
        finally:
            os.unlink(temp_path)
    
    def test_validate_invalid_json_file(self, input_validation):
        """Test validation of invalid JSON file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('not valid json {')
            temp_path = f.name
        
        try:
            valid, tasks, malformed, error = input_validation.validate_from_file(temp_path)
            
            assert valid is False
            assert 'Invalid JSON' in error
        finally:
            os.unlink(temp_path)
    
    def test_non_string_task_id(self, input_validation):
        """Test detection of non-string task_id."""
        data = [
            {'task_id': 123, 'prompt': 'Numeric task_id'}
        ]
        
        valid, tasks, malformed = input_validation.validate(data)
        
        assert valid is False
        assert len(malformed) == 1
        assert 'not a string' in malformed[0]['error'].lower()
    
    def test_non_string_prompt(self, input_validation):
        """Test detection of non-string prompt."""
        data = [
            {'task_id': 'task1', 'prompt': 123}
        ]
        
        valid, tasks, malformed = input_validation.validate(data)
        
        assert valid is False
        assert len(malformed) == 1
        assert 'not a string' in malformed[0]['error'].lower()
    
    def test_mixed_valid_and_invalid(self, input_validation):
        """Test that one malformed task doesn't corrupt the entire batch."""
        data = [
            {'task_id': 'task1', 'prompt': 'Valid task 1'},
            {'task_id': '', 'prompt': 'Invalid - empty task_id'},
            {'task_id': 'task3', 'prompt': 'Valid task 3'}
        ]
        
        valid, tasks, malformed = input_validation.validate(data)
        
        # Overall not valid due to errors
        assert valid is False
        # But valid tasks are preserved
        assert len(tasks) == 2
        assert len(malformed) == 1
        assert set(t['task_id'] for t in tasks) == {'task1', 'task3'}
