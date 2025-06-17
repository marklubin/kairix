from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

import httpx
from . import Perceptor
from ..types import Perception, Stimulus, StimulusType

logger = logging.getLogger(__name__)


class EnvironmentalContextPerceptor(Perceptor):
    """
    A perceptor that provides environmental context including:
    - Current time and date
    - Coarse location based on IP
    - Weather information
    
    This information is gathered from public APIs that don't require keys.
    """
    
    def __init__(self, cache_duration_seconds: int = 300):
        """
        Initialize the environmental context perceptor.
        
        Args:
            cache_duration_seconds: How long to cache environmental data
        """
        self.cache_duration = cache_duration_seconds
        self._cache: dict[str, tuple[str, datetime]] = {}
    
    async def perceive(self, stimulus: Stimulus) -> list[Perception]:
        """Process stimulus and return environmental context perceptions."""
        logger.info(f"EnvironmentalContextPerceptor received: {stimulus.type}")
        
        # Only respond to user messages
        if stimulus.type != StimulusType.user_message:
            logger.info("...taking no action.")
            return []
        
        # Get environmental context
        context = await self._get_environmental_context()
        
        # Create a single perception with all context
        perception = Perception(
            content=context,
            source="environmental_context",
            confidence=1.0
        )
        
        logger.debug(f"Environmental context: {context}")
        return [perception]
    
    async def _get_environmental_context(self) -> str:
        """Gather all environmental context information."""
        # Check cache first
        cache_key = "env_context"
        if cache_key in self._cache:
            content, timestamp = self._cache[cache_key]
            if (datetime.now() - timestamp).seconds < self.cache_duration:
                logger.info("Using cached environmental context")
                return content
        
        # Gather context in parallel
        tasks = [
            self._get_time_context(),
            self._get_location_context(),
            self._get_weather_context()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Build context summary
        context_parts = []
        
        # Time context (always available)
        if isinstance(results[0], str):
            context_parts.append(results[0])
        
        # Location context
        if isinstance(results[1], dict) and results[1]:
            location = results[1]
            context_parts.append(
                f"Location: {location.get('city', 'Unknown')}, "
                f"{location.get('region', '')}, "
                f"{location.get('country', '')}"
            )
        else:
            context_parts.append("Location: Unable to determine")
        
        # Weather context
        if isinstance(results[2], dict) and results[2]:
            weather = results[2]
            context_parts.append(
                f"Weather: {weather.get('description', 'Unknown')}, "
                f"Temperature: {weather.get('temperature', 'N/A')}°C, "
                f"Feels like: {weather.get('feels_like', 'N/A')}°C"
            )
        else:
            context_parts.append("Weather: Unable to determine")
        
        context = "\n".join(context_parts)
        
        # Cache the result
        self._cache[cache_key] = (context, datetime.now())
        
        return context
    
    async def _get_time_context(self) -> str:
        """Get current time and date information."""
        now = datetime.now(timezone.utc)
        local_now = datetime.now()
        
        # Format time context
        time_context = (
            f"Current UTC time: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            f"Local time: {local_now.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Day of week: {local_now.strftime('%A')}"
        )
        
        return time_context
    
    async def _get_location_context(self) -> dict[str, str]:
        """Get coarse location based on IP address."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Use ip-api.com which doesn't require an API key
                response = await client.get("http://ip-api.com/json/")
                response.raise_for_status()
                data = response.json()
                
                if data.get("status") == "success":
                    return {
                        "city": data.get("city", "Unknown"),
                        "region": data.get("regionName", ""),
                        "country": data.get("country", ""),
                        "lat": data.get("lat"),
                        "lon": data.get("lon"),
                        "timezone": data.get("timezone", "")
                    }
        except Exception as e:
            logger.warning(f"Failed to get location: {e}")
        
        return {}
    
    async def _get_weather_context(self) -> dict[str, Any]:
        """Get weather information based on location."""
        # First get location
        location = await self._get_location_context()
        if not location or "lat" not in location or "lon" not in location:
            return {}
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Use Open-Meteo API which doesn't require an API key
                lat = location["lat"]
                lon = location["lon"]
                
                url = (
                    f"https://api.open-meteo.com/v1/forecast?"
                    f"latitude={lat}&longitude={lon}"
                    f"&current_weather=true&temperature_unit=celsius"
                )
                
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                
                if "current_weather" in data:
                    current = data["current_weather"]
                    
                    # Map weather codes to descriptions
                    weather_codes = {
                        0: "Clear sky",
                        1: "Mainly clear",
                        2: "Partly cloudy", 
                        3: "Overcast",
                        45: "Foggy",
                        48: "Depositing rime fog",
                        51: "Light drizzle",
                        53: "Moderate drizzle",
                        55: "Dense drizzle",
                        61: "Slight rain",
                        63: "Moderate rain",
                        65: "Heavy rain",
                        71: "Slight snow",
                        73: "Moderate snow",
                        75: "Heavy snow",
                        80: "Slight rain showers",
                        81: "Moderate rain showers",
                        82: "Violent rain showers",
                        95: "Thunderstorm",
                        96: "Thunderstorm with slight hail",
                        99: "Thunderstorm with heavy hail"
                    }
                    
                    code = current.get("weathercode", 0)
                    description = weather_codes.get(code, "Unknown conditions")
                    
                    return {
                        "temperature": current.get("temperature"),
                        "feels_like": current.get("apparent_temperature"),
                        "description": description,
                        "wind_speed": current.get("windspeed"),
                        "wind_direction": current.get("winddirection")
                    }
        except Exception as e:
            logger.warning(f"Failed to get weather: {e}")
        
        return {}
