"""
Benchmark Loader

Loads and manages benchmark fixtures for testing.
"""

import json
import os
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path


class BenchmarkLoader:
    """Loads benchmark fixtures from JSON files."""
    
    CATEGORIES = [
        'factual_knowledge',
        'mathematical_reasoning',
        'sentiment_classification',
        'text_summarisation',
        'named_entity_recognition',
        'code_debugging',
        'logical_reasoning',
        'code_generation'
    ]
    
    def __init__(self, benchmarks_dir: Optional[str] = None):
        """
        Initialize benchmark loader.
        
        Args:
            benchmarks_dir: Directory containing benchmark JSON files
        """
        if benchmarks_dir is None:
            benchmarks_dir = os.path.join(
                os.path.dirname(__file__), 'benchmarks'
            )
        
        self._benchmarks_dir = Path(benchmarks_dir)
        self._fixtures: Dict[str, List[Dict[str, Any]]] = {}
    
    def load_all(self) -> bool:
        """
        Load all benchmark fixtures.
        
        Returns:
            True if all loaded successfully
        """
        success = True
        
        for category in self.CATEGORIES:
            loaded = self.load_category(category)
            if not loaded:
                success = False
        
        return success
    
    def load_category(self, category: str) -> bool:
        """
        Load fixtures for a specific category.
        
        Args:
            category: The category name
            
        Returns:
            True if loaded successfully
        """
        try:
            file_path = self._benchmarks_dir / f"{category}.json"
            
            if not file_path.exists():
                return False
            
            with open(file_path, 'r', encoding='utf-8') as f:
                fixtures = json.load(f)
            
            self._fixtures[category] = fixtures
            return True
            
        except Exception as e:
            return False
    
    def get_fixtures(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get fixtures for a category or all categories.
        
        Args:
            category: Optional category filter
            
        Returns:
            List of fixture dicts
        """
        if category:
            return self._fixtures.get(category, [])
        
        all_fixtures = []
        for fixtures in self._fixtures.values():
            all_fixtures.extend(fixtures)
        
        return all_fixtures
    
    def get_fixture_count(self, category: Optional[str] = None) -> int:
        """
        Get count of fixtures.
        
        Args:
            category: Optional category filter
            
        Returns:
            Number of fixtures
        """
        fixtures = self.get_fixtures(category)
        return len(fixtures)
    
    def get_tasks_json(self, categories: Optional[List[str]] = None,
                       count: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Generate a tasks.json list from fixtures.
        
        Args:
            categories: Optional list of categories to include
            count: Optional maximum number of tasks
            
        Returns:
            List of task dicts (task_id and prompt)
        """
        tasks = []
        
        if categories:
            for category in categories:
                if category in self._fixtures:
                    for fixture in self._fixtures[category]:
                        tasks.append({
                            'task_id': fixture['task_id'],
                            'prompt': fixture['prompt']
                        })
                        if count and len(tasks) >= count:
                            return tasks
        else:
            for fixtures in self._fixtures.values():
                for fixture in fixtures:
                    tasks.append({
                        'task_id': fixture['task_id'],
                        'prompt': fixture['prompt']
                    })
                    if count and len(tasks) >= count:
                        return tasks
        
        return tasks
    
    def get_expected_output(self, task_id: str) -> Optional[str]:
        """
        Get expected output for a task.
        
        Args:
            task_id: The task identifier
            
        Returns:
            Expected output or None
        """
        for fixtures in self._fixtures.values():
            for fixture in fixtures:
                if fixture['task_id'] == task_id:
                    return fixture.get('expected_output')
        
        return None
    
    def get_category_from_task_id(self, task_id: str) -> Optional[str]:
        """
        Get category for a task ID.
        
        Args:
            task_id: The task identifier
            
        Returns:
            Category or None
        """
        for category, fixtures in self._fixtures.items():
            for fixture in fixtures:
                if fixture['task_id'] == task_id:
                    return category
        
        return None
    
    def validate_expected_output(self, task_id: str, answer: str) -> bool:
        """
        Validate an answer against expected output.
        
        Args:
            task_id: The task identifier
            answer: The answer to validate
            
        Returns:
            True if answer matches expected output
        """
        expected = self.get_expected_output(task_id)
        if expected is None:
            return False
        
        # Normalize both for comparison
        expected_normalized = self._normalize_answer(expected)
        answer_normalized = self._normalize_answer(answer)
        
        return expected_normalized == answer_normalized
    
    def _normalize_answer(self, answer: str) -> str:
        """Normalize answer for comparison."""
        # Remove extra whitespace
        answer = ' '.join(answer.strip().split())
        # Normalize line breaks
        answer = answer.replace('\r\n', '\n').replace('\r', '\n')
        # Lowercase for case-insensitive comparison (optional)
        # Don't lowercase as some answers are case-sensitive
        return answer


# Singleton instance
_benchmark_loader_instance = None

def get_benchmark_loader(benchmarks_dir: Optional[str] = None) -> BenchmarkLoader:
    """Get or create the singleton benchmark loader instance."""
    global _benchmark_loader_instance
    if _benchmark_loader_instance is None:
        _benchmark_loader_instance = BenchmarkLoader(benchmarks_dir)
    return _benchmark_loader_instance
