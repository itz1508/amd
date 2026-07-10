"""
Tests for Benchmark fixtures and loader.
"""

import pytest
import os


class TestBenchmarkLoader:
    """Tests for BenchmarkLoader class."""
    
    def test_load_all(self, benchmarks_dir):
        """Test loading all benchmarks."""
        from amd_track1.benchmarks.loader import BenchmarkLoader
        
        loader = BenchmarkLoader(benchmarks_dir)
        success = loader.load_all()
        
        assert success is True
        assert loader.get_fixture_count() >= 80
    
    def test_load_single_category(self, benchmarks_dir):
        """Test loading single category."""
        from amd_track1.benchmarks.loader import BenchmarkLoader
        
        loader = BenchmarkLoader(benchmarks_dir)
        success = loader.load_category('factual_knowledge')
        
        assert success is True
        assert loader.get_fixture_count('factual_knowledge') >= 10
    
    def test_get_fixtures(self, benchmarks_dir):
        """Test getting fixtures."""
        from amd_track1.benchmarks.loader import BenchmarkLoader
        
        loader = BenchmarkLoader(benchmarks_dir)
        loader.load_all()
        
        fixtures = loader.get_fixtures()
        assert len(fixtures) >= 80
        
        fk_fixtures = loader.get_fixtures('factual_knowledge')
        assert len(fk_fixtures) >= 10
    
    def test_get_fixture_count(self, benchmarks_dir):
        """Test getting fixture count."""
        from amd_track1.benchmarks.loader import BenchmarkLoader
        
        loader = BenchmarkLoader(benchmarks_dir)
        loader.load_all()
        
        count = loader.get_fixture_count()
        assert count >= 80
        
        fk_count = loader.get_fixture_count('factual_knowledge')
        assert fk_count >= 10
    
    def test_get_tasks_json(self, benchmarks_dir):
        """Test generating tasks.json."""
        from amd_track1.benchmarks.loader import BenchmarkLoader
        
        loader = BenchmarkLoader(benchmarks_dir)
        loader.load_all()
        
        tasks = loader.get_tasks_json()
        assert len(tasks) >= 80
        
        # Check structure
        for task in tasks:
            assert 'task_id' in task
            assert 'prompt' in task
        
        # Check all categories are represented
        categories = set()
        for task in tasks:
            category = loader.get_category_from_task_id(task['task_id'])
            if category:
                categories.add(category)
        
        assert len(categories) == 8
    
    def test_get_tasks_json_with_count(self, benchmarks_dir):
        """Test generating tasks.json with count limit."""
        from amd_track1.benchmarks.loader import BenchmarkLoader
        
        loader = BenchmarkLoader(benchmarks_dir)
        loader.load_all()
        
        tasks = loader.get_tasks_json(count=10)
        assert len(tasks) == 10
    
    def test_get_tasks_json_with_categories(self, benchmarks_dir):
        """Test generating tasks.json with specific categories."""
        from amd_track1.benchmarks.loader import BenchmarkLoader
        
        loader = BenchmarkLoader(benchmarks_dir)
        loader.load_all()
        
        tasks = loader.get_tasks_json(categories=['factual_knowledge', 'mathematical_reasoning'])
        
        # All tasks should be from specified categories
        for task in tasks:
            category = loader.get_category_from_task_id(task['task_id'])
            assert category in ['factual_knowledge', 'mathematical_reasoning']
    
    def test_get_expected_output(self, benchmarks_dir):
        """Test getting expected output."""
        from amd_track1.benchmarks.loader import BenchmarkLoader
        
        loader = BenchmarkLoader(benchmarks_dir)
        loader.load_all()
        
        # Get a known task ID
        fixtures = loader.get_fixtures('factual_knowledge')
        if fixtures:
            task_id = fixtures[0]['task_id']
            expected = loader.get_expected_output(task_id)
            assert expected is not None
    
    def test_get_category_from_task_id(self, benchmarks_dir):
        """Test getting category from task ID."""
        from amd_track1.benchmarks.loader import BenchmarkLoader
        
        loader = BenchmarkLoader(benchmarks_dir)
        loader.load_all()
        
        fixtures = loader.get_fixtures('factual_knowledge')
        if fixtures:
            task_id = fixtures[0]['task_id']
            category = loader.get_category_from_task_id(task_id)
            assert category == 'factual_knowledge'
    
    def test_validate_expected_output(self, benchmarks_dir):
        """Test validating answer against expected output."""
        from amd_track1.benchmarks.loader import BenchmarkLoader
        
        loader = BenchmarkLoader(benchmarks_dir)
        loader.load_all()
        
        fixtures = loader.get_fixtures('factual_knowledge')
        if fixtures:
            task_id = fixtures[0]['task_id']
            expected = loader.get_expected_output(task_id)
            if expected:
                assert loader.validate_expected_output(task_id, expected) is True


class TestBenchmarkFixtures:
    """Tests for benchmark fixture files."""
    
    def test_factual_knowledge_fixtures(self, benchmarks_dir):
        """Test factual knowledge fixtures."""
        import json
        
        with open(os.path.join(benchmarks_dir, 'factual_knowledge.json'), 'r') as f:
            fixtures = json.load(f)
        
        assert len(fixtures) >= 10
        for fixture in fixtures:
            assert 'task_id' in fixture
            assert 'prompt' in fixture
            assert 'expected_output' in fixture
            assert 'category' in fixture
    
    def test_mathematical_reasoning_fixtures(self, benchmarks_dir):
        """Test mathematical reasoning fixtures."""
        import json
        
        with open(os.path.join(benchmarks_dir, 'mathematical_reasoning.json'), 'r') as f:
            fixtures = json.load(f)
        
        assert len(fixtures) >= 10
        for fixture in fixtures:
            assert 'task_id' in fixture
            assert 'prompt' in fixture
            assert 'expected_output' in fixture
    
    def test_sentiment_classification_fixtures(self, benchmarks_dir):
        """Test sentiment classification fixtures."""
        import json
        
        with open(os.path.join(benchmarks_dir, 'sentiment_classification.json'), 'r') as f:
            fixtures = json.load(f)
        
        assert len(fixtures) >= 10
        for fixture in fixtures:
            assert fixture['category'] == 'sentiment_classification'
            assert fixture['expected_output'] in ['positive', 'negative', 'neutral']
    
    def test_text_summarisation_fixtures(self, benchmarks_dir):
        """Test text summarisation fixtures."""
        import json
        
        with open(os.path.join(benchmarks_dir, 'text_summarisation.json'), 'r') as f:
            fixtures = json.load(f)
        
        assert len(fixtures) >= 10
    
    def test_named_entity_recognition_fixtures(self, benchmarks_dir):
        """Test NER fixtures."""
        import json
        
        with open(os.path.join(benchmarks_dir, 'named_entity_recognition.json'), 'r') as f:
            fixtures = json.load(f)
        
        assert len(fixtures) >= 10
        for fixture in fixtures:
            assert 'category' in fixture
            assert fixture['category'] == 'named_entity_recognition'
    
    def test_code_debugging_fixtures(self, benchmarks_dir):
        """Test code debugging fixtures."""
        import json
        
        with open(os.path.join(benchmarks_dir, 'code_debugging.json'), 'r') as f:
            fixtures = json.load(f)
        
        assert len(fixtures) >= 10
        for fixture in fixtures:
            assert 'category' in fixture
            assert fixture['category'] == 'code_debugging'
    
    def test_logical_reasoning_fixtures(self, benchmarks_dir):
        """Test logical reasoning fixtures."""
        import json
        
        with open(os.path.join(benchmarks_dir, 'logical_reasoning.json'), 'r') as f:
            fixtures = json.load(f)
        
        assert len(fixtures) >= 10
        for fixture in fixtures:
            assert 'category' in fixture
            assert fixture['category'] == 'logical_reasoning'
    
    def test_code_generation_fixtures(self, benchmarks_dir):
        """Test code generation fixtures."""
        import json
        
        with open(os.path.join(benchmarks_dir, 'code_generation.json'), 'r') as f:
            fixtures = json.load(f)
        
        assert len(fixtures) >= 10
        for fixture in fixtures:
            assert 'category' in fixture
            assert fixture['category'] == 'code_generation'
    
    def test_all_categories_have_10_fixtures(self, benchmarks_dir):
        """Test that all categories have at least 10 fixtures."""
        import json
        
        categories = [
            'factual_knowledge',
            'mathematical_reasoning',
            'sentiment_classification',
            'text_summarisation',
            'named_entity_recognition',
            'code_debugging',
            'logical_reasoning',
            'code_generation'
        ]
        
        for category in categories:
            with open(os.path.join(benchmarks_dir, f'{category}.json'), 'r') as f:
                fixtures = json.load(f)
            assert len(fixtures) >= 10, f"Category {category} has only {len(fixtures)} fixtures"
