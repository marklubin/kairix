"""Test implementation for cognition.perceptor base class."""

import pytest
from abc import ABC
from typing import List
import asyncio

from kairix_core.cognition.perceptor import Perceptor
from kairix_core.types.cognition import Stimulus, Perception, StimulusType


class TestPerceptorBase:
    """Test cases for Perceptor abstract base class."""
    
    def test_perceptor_is_abstract(self):
        """Test that Perceptor cannot be instantiated directly."""
        with pytest.raises(TypeError) as exc_info:
            Perceptor()
        
        assert "Can't instantiate abstract class Perceptor" in str(exc_info.value)
        assert "perceive" in str(exc_info.value)
    
    def test_perceptor_requires_perceive_implementation(self):
        """Test that subclasses must implement perceive method."""
        # Create a subclass without implementing perceive
        class IncompletePerceptor(Perceptor):
            pass
        
        with pytest.raises(TypeError) as exc_info:
            IncompletePerceptor()
        
        assert "Can't instantiate abstract class IncompletePerceptor" in str(exc_info.value)
        assert "perceive" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_valid_perceptor_implementation(self):
        """Test a valid Perceptor subclass implementation."""
        # Create a proper subclass
        class ValidPerceptor(Perceptor):
            async def perceive(self, stimulus: Stimulus) -> List[Perception]:
                return [Perception(
                    source="test_perceptor",
                    content=f"Perceived: {stimulus.content}",
                    confidence=0.9
                )]
        
        # Should instantiate successfully
        perceptor = ValidPerceptor()
        assert isinstance(perceptor, Perceptor)
        
        # Test perceive method
        stimulus = Stimulus(content="test input", type=StimulusType.user_message)
        perceptions = await perceptor.perceive(stimulus)
        
        assert len(perceptions) == 1
        assert perceptions[0].source == "test_perceptor"
        assert "Perceived: test input" in perceptions[0].content
        assert perceptions[0].confidence == 0.9
    
    @pytest.mark.asyncio
    async def test_perceptor_with_empty_perceptions(self):
        """Test perceptor that returns empty perception list."""
        class EmptyPerceptor(Perceptor):
            async def perceive(self, stimulus: Stimulus) -> List[Perception]:
                return []
        
        perceptor = EmptyPerceptor()
        stimulus = Stimulus(content="test", type=StimulusType.time_tick)
        perceptions = await perceptor.perceive(stimulus)
        
        assert perceptions == []
        assert isinstance(perceptions, list)
    
    @pytest.mark.asyncio
    async def test_perceptor_with_multiple_perceptions(self):
        """Test perceptor that returns multiple perceptions."""
        class MultiPerceptor(Perceptor):
            async def perceive(self, stimulus: Stimulus) -> List[Perception]:
                return [
                    Perception(source="multi", content="First perception", confidence=0.8),
                    Perception(source="multi", content="Second perception", confidence=0.7),
                    Perception(source="multi", content="Third perception", confidence=0.6)
                ]
        
        perceptor = MultiPerceptor()
        stimulus = Stimulus(content="test", type=StimulusType.user_message)
        perceptions = await perceptor.perceive(stimulus)
        
        assert len(perceptions) == 3
        assert all(p.source == "multi" for p in perceptions)
        assert perceptions[0].confidence == 0.8
        assert perceptions[1].confidence == 0.7
        assert perceptions[2].confidence == 0.6
    
    @pytest.mark.asyncio
    async def test_perceptor_error_handling(self):
        """Test error handling in perceptor implementation."""
        class ErrorPerceptor(Perceptor):
            async def perceive(self, stimulus: Stimulus) -> List[Perception]:
                if stimulus.content == "error":
                    raise ValueError("Test error in perceive")
                return [Perception(source="error_test", content="OK", confidence=1.0)]
        
        perceptor = ErrorPerceptor()
        
        # Normal case
        stimulus = Stimulus(content="normal", type=StimulusType.user_message)
        perceptions = await perceptor.perceive(stimulus)
        assert len(perceptions) == 1
        assert perceptions[0].content == "OK"
        
        # Error case
        error_stimulus = Stimulus(content="error", type=StimulusType.user_message)
        with pytest.raises(ValueError) as exc_info:
            await perceptor.perceive(error_stimulus)
        assert "Test error in perceive" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_perceptor_async_behavior(self):
        """Test that perceive method is properly async."""
        class AsyncPerceptor(Perceptor):
            async def perceive(self, stimulus: Stimulus) -> List[Perception]:
                # Simulate async operation
                await asyncio.sleep(0.01)
                return [Perception(
                    source="async",
                    content=f"Async processed: {stimulus.content}",
                    confidence=1.0
                )]
        
        perceptor = AsyncPerceptor()
        stimulus = Stimulus(content="async test", type=StimulusType.user_message)
        
        # Verify it returns a coroutine
        coro = perceptor.perceive(stimulus)
        assert asyncio.iscoroutine(coro)
        
        # Execute and verify result
        perceptions = await coro
        assert len(perceptions) == 1
        assert "Async processed: async test" in perceptions[0].content
    
    def test_perceptor_inheritance_chain(self):
        """Test Perceptor inheritance from ABC."""
        assert issubclass(Perceptor, ABC)
        assert hasattr(Perceptor, 'perceive')
        assert hasattr(Perceptor.perceive, '__isabstractmethod__')
        assert Perceptor.perceive.__isabstractmethod__ is True
    
    def test_module_exports(self):
        """Test that __all__ exports are correct."""
        from kairix_core.cognition import perceptor
        
        assert hasattr(perceptor, '__all__')
        assert 'Perceptor' in perceptor.__all__
        assert len(perceptor.__all__) == 1  # Only Perceptor should be exported
        
        # Verify Perceptor is accessible
        assert perceptor.Perceptor is Perceptor
    
    @pytest.mark.asyncio
    async def test_perceptor_with_different_stimulus_types(self):
        """Test perceptor handling different stimulus types."""
        class TypeAwarePerceptor(Perceptor):
            async def perceive(self, stimulus: Stimulus) -> List[Perception]:
                type_responses = {
                    StimulusType.user_message: "User said: ",
                    StimulusType.time_tick: "Time update: ",
                    StimulusType.self_perception: "Self reflection: "
                }
                
                prefix = type_responses.get(stimulus.type, "Unknown: ")
                
                return [Perception(
                    source="type_aware",
                    content=f"{prefix}{stimulus.content}",
                    confidence=0.95
                )]
        
        perceptor = TypeAwarePerceptor()
        
        # Test different stimulus types
        test_cases = [
            (StimulusType.user_message, "Hello", "User said: Hello"),
            (StimulusType.time_tick, "2024-01-01", "Time update: 2024-01-01"),
            (StimulusType.self_perception, "Thinking", "Self reflection: Thinking")
        ]
        
        for stim_type, content, expected_prefix in test_cases:
            stimulus = Stimulus(content=content, type=stim_type)
            perceptions = await perceptor.perceive(stimulus)
            
            assert len(perceptions) == 1
            assert perceptions[0].content == expected_prefix
            assert perceptions[0].confidence == 0.95
    
    def test_perceptor_type_annotations(self):
        """Test that Perceptor has correct type annotations."""
        import inspect
        
        # Get the perceive method
        perceive_method = Perceptor.perceive
        
        # Get type hints
        sig = inspect.signature(perceive_method)
        
        # Check parameter types
        params = sig.parameters
        assert 'stimulus' in params
        assert params['stimulus'].annotation.__name__ == 'Stimulus'
        
        # Check return type (should be List[Perception])
        return_annotation = sig.return_annotation
        assert hasattr(return_annotation, '__origin__')  # It's a generic type
        assert return_annotation.__origin__ is list or str(return_annotation).startswith('typing.List')