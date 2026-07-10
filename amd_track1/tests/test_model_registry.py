"""
Tests for Model Registry.
"""

import pytest


class TestModelRegistry:
    """Tests for ModelRegistry class."""
    
    def test_initialize(self, model_registry):
        """Test initialization with allowed models."""
        models = model_registry.get_allowed_models()
        assert len(models) == 3
        assert 'model1' in models
    
    def test_is_model_allowed(self, model_registry):
        """Test model allowed checking."""
        assert model_registry.is_model_allowed('model1') is True
        assert model_registry.is_model_allowed('unknown_model') is False
    
    def test_get_model(self, model_registry):
        """Test getting model by ID."""
        model = model_registry.get_model('model1')
        assert model is not None
        assert model.model_id == 'model1'
        
        model = model_registry.get_model('unknown')
        assert model is None
    
    def test_record_probe_result(self, model_registry):
        """Test recording probe result."""
        success = model_registry.record_probe_result('model1', True, 0.5, None)
        assert success is True
        
        model = model_registry.get_model('model1')
        assert model.successful_probe is True
        assert model.latency == 0.5
        assert model.error is None
        assert model.available is True
    
    def test_record_probe_result_failure(self, model_registry):
        """Test recording failed probe result."""
        success = model_registry.record_probe_result('model1', False, None, 'Connection error')
        assert success is True
        
        model = model_registry.get_model('model1')
        assert model.successful_probe is False
        assert model.error == 'Connection error'
        assert model.available is False
    
    def test_record_category_result(self, model_registry):
        """Test recording category result."""
        success = model_registry.record_category_result(
            'model1', 'factual_knowledge',
            success=True, input_tokens=100, output_tokens=50, latency=1.0
        )
        assert success is True
        
        stats = model_registry.get_category_stats('model1', 'factual_knowledge')
        assert stats is not None
        assert stats['attempts'] == 1
        assert stats['successes'] == 1
        assert stats['total_input_tokens'] == 100
        assert stats['total_output_tokens'] == 50
    
    def test_get_success_rate_category(self, model_registry):
        """Test getting success rate for category."""
        # Record some results
        model_registry.record_category_result('model1', 'factual_knowledge', True)
        model_registry.record_category_result('model1', 'factual_knowledge', True)
        model_registry.record_category_result('model1', 'factual_knowledge', False)
        
        rate = model_registry.get_success_rate('model1', 'factual_knowledge')
        assert rate == pytest.approx(2/3, rel=0.01)
    
    def test_get_success_rate_overall(self, model_registry):
        """Test getting overall success rate."""
        model_registry.record_category_result('model1', 'factual_knowledge', True)
        model_registry.record_category_result('model1', 'mathematical_reasoning', False)
        
        rate = model_registry.get_success_rate('model1')
        assert rate == pytest.approx(0.5, rel=0.01)
    
    def test_get_average_tokens(self, model_registry):
        """Test getting average tokens."""
        model_registry.record_category_result('model1', 'factual_knowledge',
                                               True, input_tokens=100, output_tokens=50)
        model_registry.record_category_result('model1', 'factual_knowledge',
                                               True, input_tokens=200, output_tokens=100)
        
        avg_input, avg_output = model_registry.get_average_tokens('model1', 'factual_knowledge')
        assert avg_input == 150
        assert avg_output == 75
    
    def test_get_available_models(self, model_registry):
        """Test getting available models."""
        # Initially all are available
        available = model_registry.get_available_models()
        assert len(available) == 3
        
        # Mark one as unavailable
        model_registry.record_probe_result('model1', False)
        
        available = model_registry.get_available_models()
        assert len(available) == 2
        assert 'model1' not in available
    
    def test_to_dict_and_from_dict(self, model_registry):
        """Test serialization and deserialization."""
        # Record some data
        model_registry.record_probe_result('model1', True, 0.5)
        model_registry.record_category_result('model1', 'factual_knowledge', True)
        
        # Serialize
        data = model_registry.to_dict()
        
        # Deserialize
        from amd_track1.model_registry import ModelRegistry
        new_registry = ModelRegistry.from_dict(data)
        
        # Verify
        assert new_registry.get_model('model1').successful_probe is True
        assert new_registry.get_category_stats('model1', 'factual_knowledge') is not None


class TestModelRecord:
    """Tests for ModelRecord dataclass."""
    
    def test_to_dict(self):
        """Test ModelRecord to_dict."""
        from amd_track1.model_registry import ModelRecord
        
        record = ModelRecord(
            model_id='test_model',
            available=True,
            successful_probe=True,
            latency=0.5
        )
        
        data = record.to_dict()
        assert data['model_id'] == 'test_model'
        assert data['available'] is True
        assert data['latency'] == 0.5
    
    def test_from_dict(self):
        """Test ModelRecord from_dict."""
        from amd_track1.model_registry import ModelRecord
        
        data = {
            'model_id': 'test_model',
            'available': True,
            'successful_probe': True,
            'latency': 0.5
        }
        
        record = ModelRecord.from_dict(data)
        assert record.model_id == 'test_model'
        assert record.available is True
        assert record.latency == 0.5
