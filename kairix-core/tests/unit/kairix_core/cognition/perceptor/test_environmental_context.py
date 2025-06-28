"""Test implementation for EnvironmentalContextPerceptor."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone, timedelta
import httpx
import asyncio

from kairix_core.cognition.perceptor.environmental_context import EnvironmentalContextPerceptor
from kairix_core.types.cognition import Stimulus, StimulusType


class TestEnvironmentalContextPerceptor:
    """Test cases for EnvironmentalContextPerceptor class."""
    
    @pytest.fixture
    def mock_httpx_client(self):
        """Mock httpx AsyncClient."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.json = Mock()
        mock_response.raise_for_status = Mock()
        mock_client.get = AsyncMock(return_value=mock_response)
        
        with patch('httpx.AsyncClient') as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client
            mock_async_client.return_value.__aexit__.return_value = None
            yield mock_client, mock_response
    
    def test_initialization(self):
        """Test EnvironmentalContextPerceptor initialization."""
        # Test with default cache duration
        perceptor = EnvironmentalContextPerceptor()
        assert perceptor.cache_duration == 300
        assert perceptor._cache == {}
        
        # Test with custom cache duration
        perceptor_custom = EnvironmentalContextPerceptor(cache_duration_seconds=600)
        assert perceptor_custom.cache_duration == 600
    
    @pytest.mark.asyncio
    async def test_perceive_user_message(self, mock_httpx_client):
        """Test perceive method with user_message stimulus."""
        mock_client, mock_response = mock_httpx_client
        
        # Set up mock responses
        location_data = {
            "status": "success",
            "city": "San Francisco",
            "regionName": "California",
            "country": "United States",
            "lat": 37.7749,
            "lon": -122.4194,
            "timezone": "America/Los_Angeles"
        }
        
        weather_data = {
            "current_weather": {
                "temperature": 20.5,
                "apparent_temperature": 18.2,
                "weathercode": 2,
                "windspeed": 10.5,
                "winddirection": 180
            }
        }
        
        # Configure mock to return different responses for different URLs
        def side_effect(url):
            response = Mock()
            response.raise_for_status = Mock()
            if "ip-api.com" in url:
                response.json = Mock(return_value=location_data)
            elif "open-meteo.com" in url:
                response.json = Mock(return_value=weather_data)
            return response
        
        mock_client.get.side_effect = side_effect
        
        perceptor = EnvironmentalContextPerceptor()
        
        stimulus = Stimulus(
            content="What's the weather?",
            type=StimulusType.user_message
        )
        
        # Mock datetime for consistent testing
        with patch('kairix_core.cognition.perceptor.environmental_context.datetime') as mock_datetime:
            mock_now = datetime(2024, 1, 15, 14, 30, 0)
            mock_utc_now = datetime(2024, 1, 15, 22, 30, 0, tzinfo=timezone.utc)
            
            # Mock datetime.now with different behaviors
            def now_side_effect(tz=None):
                if tz == timezone.utc:
                    return mock_utc_now
                return mock_now
            
            mock_datetime.now.side_effect = now_side_effect
            mock_datetime.strftime = datetime.strftime
            
            perceptions = await perceptor.perceive(stimulus)
        
        # Verify perception
        assert len(perceptions) == 1
        perception = perceptions[0]
        assert perception.source == "environmental_context"
        assert perception.confidence == 1.0
        
        # Verify content includes expected information
        content = perception.content
        assert "Current UTC time: 2024-01-15 22:30:00 UTC" in content
        assert "Local time: 2024-01-15 14:30:00" in content
        assert "Day of week: Monday" in content
        assert "Location: San Francisco, California, United States" in content
        assert "Weather: Partly cloudy" in content
        assert "Temperature: 20.5°C" in content
        assert "Feels like: 18.2°C" in content
    
    @pytest.mark.asyncio
    async def test_perceive_non_user_message(self):
        """Test perceive method with non-user_message stimulus types."""
        perceptor = EnvironmentalContextPerceptor()
        
        # Test with time_tick
        stimulus = Stimulus(
            content="2024-01-01T12:00:00",
            type=StimulusType.time_tick
        )
        
        perceptions = await perceptor.perceive(stimulus)
        assert perceptions == []
        
        # Test with self_perception
        stimulus = Stimulus(
            content="Internal thought",
            type=StimulusType.self_perception
        )
        
        perceptions = await perceptor.perceive(stimulus)
        assert perceptions == []
    
    @pytest.mark.asyncio
    async def test_location_api_failure(self, mock_httpx_client):
        """Test handling of location API failure."""
        mock_client, _ = mock_httpx_client
        
        # Make location API fail
        mock_client.get.side_effect = httpx.RequestError("Connection failed")
        
        perceptor = EnvironmentalContextPerceptor()
        
        stimulus = Stimulus(content="test", type=StimulusType.user_message)
        perceptions = await perceptor.perceive(stimulus)
        
        assert len(perceptions) == 1
        content = perceptions[0].content
        assert "Location: Unable to determine" in content
        assert "Weather: Unable to determine" in content  # Weather depends on location
    
    @pytest.mark.asyncio
    async def test_location_api_bad_response(self, mock_httpx_client):
        """Test handling of location API returning error status."""
        mock_client, mock_response = mock_httpx_client
        
        # Location API returns error status
        mock_response.json.return_value = {"status": "fail", "message": "private IP"}
        
        perceptor = EnvironmentalContextPerceptor()
        
        stimulus = Stimulus(content="test", type=StimulusType.user_message)
        perceptions = await perceptor.perceive(stimulus)
        
        assert len(perceptions) == 1
        content = perceptions[0].content
        assert "Location: Unable to determine" in content
    
    @pytest.mark.asyncio
    async def test_weather_api_failure(self, mock_httpx_client):
        """Test handling of weather API failure."""
        mock_client, mock_response = mock_httpx_client
        
        # Location succeeds
        location_data = {
            "status": "success",
            "city": "London",
            "regionName": "England",
            "country": "United Kingdom",
            "lat": 51.5074,
            "lon": -0.1278
        }
        
        # Configure responses
        def side_effect(url):
            if "ip-api.com" in url:
                response = Mock()
                response.raise_for_status = Mock()
                response.json = Mock(return_value=location_data)
                return response
            elif "open-meteo.com" in url:
                raise httpx.HTTPStatusError("503 Service Unavailable", request=Mock(), response=Mock())
        
        mock_client.get.side_effect = side_effect
        
        perceptor = EnvironmentalContextPerceptor()
        
        stimulus = Stimulus(content="test", type=StimulusType.user_message)
        perceptions = await perceptor.perceive(stimulus)
        
        assert len(perceptions) == 1
        content = perceptions[0].content
        assert "Location: London, England, United Kingdom" in content
        assert "Weather: Unable to determine" in content
    
    @pytest.mark.asyncio
    async def test_caching_behavior(self, mock_httpx_client):
        """Test that results are cached and reused within cache duration."""
        mock_client, mock_response = mock_httpx_client
        
        # Set up successful responses
        location_data = {"status": "success", "city": "Tokyo", "lat": 35.6762, "lon": 139.6503}
        weather_data = {"current_weather": {"temperature": 15.0, "weathercode": 0}}
        
        def side_effect(url):
            response = Mock()
            response.raise_for_status = Mock()
            if "ip-api.com" in url:
                response.json = Mock(return_value=location_data)
            elif "open-meteo.com" in url:
                response.json = Mock(return_value=weather_data)
            return response
        
        mock_client.get.side_effect = side_effect
        
        perceptor = EnvironmentalContextPerceptor(cache_duration_seconds=10)
        
        # First request
        stimulus = Stimulus(content="test", type=StimulusType.user_message)
        perceptions1 = await perceptor.perceive(stimulus)
        
        # Verify API was called (location is called twice: once directly, once by weather)
        assert mock_client.get.call_count >= 2
        
        # Second request (should use cache)
        mock_client.get.reset_mock()
        perceptions2 = await perceptor.perceive(stimulus)
        
        # Verify API was NOT called
        assert mock_client.get.call_count == 0
        
        # Results should be identical
        assert perceptions1[0].content == perceptions2[0].content
    
    @pytest.mark.asyncio
    async def test_cache_expiration(self, mock_httpx_client):
        """Test that cache expires after duration."""
        mock_client, mock_response = mock_httpx_client
        
        location_data = {"status": "success", "city": "Paris", "lat": 48.8566, "lon": 2.3522}
        mock_response.json.return_value = location_data
        
        perceptor = EnvironmentalContextPerceptor(cache_duration_seconds=1)
        
        # First request
        stimulus = Stimulus(content="test", type=StimulusType.user_message)
        await perceptor.perceive(stimulus)
        
        # Manually expire cache by modifying timestamp
        cache_key = "env_context"
        content, _ = perceptor._cache[cache_key]
        perceptor._cache[cache_key] = (content, datetime.now() - timedelta(seconds=2))
        
        # Second request (should call API again)
        mock_client.get.reset_mock()
        await perceptor.perceive(stimulus)
        
        # Verify API was called again
        assert mock_client.get.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_time_context_formatting(self):
        """Test time context formatting."""
        perceptor = EnvironmentalContextPerceptor()
        
        with patch('kairix_core.cognition.perceptor.environmental_context.datetime') as mock_datetime:
            # Set up specific times
            local_time = datetime(2024, 3, 15, 9, 45, 30)
            utc_time = datetime(2024, 3, 15, 17, 45, 30, tzinfo=timezone.utc)
            
            def now_side_effect(tz=None):
                if tz == timezone.utc:
                    return utc_time
                return local_time
            
            mock_datetime.now.side_effect = now_side_effect
            
            time_context = await perceptor._get_time_context()
            
            assert "Current UTC time: 2024-03-15 17:45:30 UTC" in time_context
            assert "Local time: 2024-03-15 09:45:30" in time_context
            assert "Day of week: Friday" in time_context
    
    @pytest.mark.asyncio
    async def test_weather_code_mapping(self, mock_httpx_client):
        """Test various weather code mappings."""
        mock_client, _ = mock_httpx_client
        
        perceptor = EnvironmentalContextPerceptor()
        
        # Test different weather codes
        weather_codes_to_test = [
            (0, "Clear sky"),
            (3, "Overcast"),
            (61, "Slight rain"),
            (75, "Heavy snow"),
            (95, "Thunderstorm"),
            (999, "Unknown conditions")  # Unknown code
        ]
        
        for code, expected_description in weather_codes_to_test:
            weather_data = {
                "current_weather": {
                    "temperature": 20,
                    "apparent_temperature": 18,
                    "weathercode": code
                }
            }
            
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_response.json = Mock(return_value=weather_data)
            mock_client.get.return_value = mock_response
            
            # Need location first
            location = {"lat": 40.7128, "lon": -74.0060}
            weather = await perceptor._get_weather_context()
            
            # Since _get_weather_context calls _get_location_context first,
            # we'll test the weather code mapping directly
            with patch.object(perceptor, '_get_location_context', return_value=location):
                weather = await perceptor._get_weather_context()
                assert weather.get("description") == expected_description
    
    @pytest.mark.asyncio
    async def test_partial_data_handling(self, mock_httpx_client):
        """Test handling of partial data from APIs."""
        mock_client, mock_response = mock_httpx_client
        
        # Location with missing fields
        location_data = {
            "status": "success",
            "city": "Unknown City",
            # Missing other fields
        }
        
        mock_response.json.return_value = location_data
        
        perceptor = EnvironmentalContextPerceptor()
        
        stimulus = Stimulus(content="test", type=StimulusType.user_message)
        perceptions = await perceptor.perceive(stimulus)
        
        content = perceptions[0].content
        assert "Location: Unknown City, , " in content
        assert "Weather: Unable to determine" in content  # No lat/lon for weather
    
    @pytest.mark.asyncio
    async def test_concurrent_api_calls(self, mock_httpx_client):
        """Test that location and weather APIs are called concurrently."""
        mock_client, _ = mock_httpx_client
        
        call_times = []
        
        async def mock_get(url):
            call_times.append(datetime.now())
            # Simulate API delay
            await asyncio.sleep(0.1)
            
            response = Mock()
            response.raise_for_status = Mock()
            
            if "ip-api.com" in url:
                response.json = Mock(return_value={
                    "status": "success",
                    "city": "Berlin",
                    "lat": 52.5200,
                    "lon": 13.4050
                })
            else:
                response.json = Mock(return_value={
                    "current_weather": {"temperature": 10, "weathercode": 1}
                })
            
            return response
        
        mock_client.get = mock_get
        
        perceptor = EnvironmentalContextPerceptor()
        
        stimulus = Stimulus(content="test", type=StimulusType.user_message)
        await perceptor.perceive(stimulus)
        
        # Verify both calls were made
        assert len(call_times) >= 2
        
        # They should start close together (concurrent)
        time_diff = (call_times[1] - call_times[0]).total_seconds()
        assert time_diff < 0.05  # Should be nearly simultaneous