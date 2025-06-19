from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from kairix_core.types.cognition import Stimulus, StimulusType

from kairix_core.cognition.perceptor.environmental_context import (
    EnvironmentalContextPerceptor,
)


class TestEnvironmentalContextPerceptor:
    """Test cases for EnvironmentalContextPerceptor"""

    @pytest.fixture
    def perceptor(self):
        """Create a perceptor instance with short cache duration for testing"""
        return EnvironmentalContextPerceptor(cache_duration_seconds=1)

    @pytest.mark.asyncio
    async def test_only_responds_to_user_messages(self, perceptor):
        """Test that perceptor only responds to user_message stimuli"""
        # Test with non-user message
        stimulus = Stimulus("test", StimulusType.execution_attempt)
        perceptions = await perceptor.perceive(stimulus)
        assert perceptions == []

        # Test with user message
        stimulus = Stimulus("What's the weather?", StimulusType.user_message)
        with patch.object(perceptor, "_get_environmental_context") as mock_context:
            mock_context.return_value = "Test context"
            perceptions = await perceptor.perceive(stimulus)
            assert len(perceptions) == 1
            assert perceptions[0].content == "Test context"
            assert perceptions[0].source == "environmental_context"

    @pytest.mark.asyncio
    async def test_time_context(self, perceptor):
        """Test time context generation"""
        time_context = await perceptor._get_time_context()

        # Check that it contains expected elements
        assert "Current UTC time:" in time_context
        assert "Local time:" in time_context
        assert "Day of week:" in time_context

        # Verify it contains actual time info
        assert datetime.now().strftime("%Y-%m-%d") in time_context

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_location_context_success(self, mock_get, perceptor):
        """Test successful location retrieval"""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "success",
            "city": "San Francisco",
            "regionName": "California",
            "country": "United States",
            "lat": 37.7749,
            "lon": -122.4194,
            "timezone": "America/Los_Angeles",
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        location = await perceptor._get_location_context()

        assert location["city"] == "San Francisco"
        assert location["region"] == "California"
        assert location["country"] == "United States"
        assert location["lat"] == 37.7749
        assert location["lon"] == -122.4194

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_location_context_failure(self, mock_get, perceptor):
        """Test location retrieval failure handling"""
        # Mock failed response
        mock_get.side_effect = Exception("Network error")

        location = await perceptor._get_location_context()
        assert location == {}

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_weather_context_success(self, mock_get, perceptor):
        """Test successful weather retrieval"""
        # First mock location call
        with patch.object(perceptor, "_get_location_context") as mock_location:
            mock_location.return_value = {"lat": 37.7749, "lon": -122.4194}

            # Mock weather response
            mock_response = Mock()
            mock_response.json.return_value = {
                "current_weather": {
                    "temperature": 20.5,
                    "apparent_temperature": 18.2,
                    "weathercode": 2,  # Partly cloudy
                    "windspeed": 15.0,
                    "winddirection": 180,
                }
            }
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            weather = await perceptor._get_weather_context()

            assert weather["temperature"] == 20.5
            assert weather["feels_like"] == 18.2
            assert weather["description"] == "Partly cloudy"
            assert weather["wind_speed"] == 15.0

    @pytest.mark.asyncio
    async def test_weather_context_no_location(self, perceptor):
        """Test weather retrieval when location is unavailable"""
        with patch.object(perceptor, "_get_location_context") as mock_location:
            mock_location.return_value = {}

            weather = await perceptor._get_weather_context()
            assert weather == {}

    @pytest.mark.asyncio
    @patch.object(EnvironmentalContextPerceptor, "_get_time_context")
    @patch.object(EnvironmentalContextPerceptor, "_get_location_context")
    @patch.object(EnvironmentalContextPerceptor, "_get_weather_context")
    async def test_full_environmental_context(self, mock_weather, mock_location, mock_time, perceptor):
        """Test full environmental context assembly"""
        # Mock all components
        mock_time.return_value = "Current UTC time: 2024-01-01 12:00:00 UTC"
        mock_location.return_value = {"city": "San Francisco", "region": "California", "country": "United States"}
        mock_weather.return_value = {"description": "Clear sky", "temperature": 22, "feels_like": 20}

        context = await perceptor._get_environmental_context()

        # Check all components are present
        assert "Current UTC time: 2024-01-01 12:00:00 UTC" in context
        assert "Location: San Francisco, California, United States" in context
        assert "Weather: Clear sky" in context
        assert "Temperature: 22°C" in context
        assert "Feels like: 20°C" in context

    @pytest.mark.asyncio
    async def test_caching(self, perceptor):
        """Test that environmental context is cached"""
        call_tracker = {"count": 0}

        async def mock_context():
            call_tracker["count"] += 1
            return f"Context {call_tracker['count']}"

        with (
            patch.object(perceptor, "_get_time_context") as mock_time,
            patch.object(perceptor, "_get_location_context") as mock_loc,
            patch.object(perceptor, "_get_weather_context") as mock_weather,
        ):
            mock_time.return_value = "Time"
            mock_loc.return_value = {}
            mock_weather.return_value = {}

            # First call should fetch fresh data
            context1 = await perceptor._get_environmental_context()
            assert mock_time.call_count == 1

            # Second call should use cache
            context2 = await perceptor._get_environmental_context()
            assert mock_time.call_count == 1  # No additional calls
            assert context1 == context2

            # Wait for cache to expire
            import asyncio

            await asyncio.sleep(1.1)

            # Third call should fetch fresh data again
            await perceptor._get_environmental_context()
            assert mock_time.call_count == 2
