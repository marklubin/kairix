from datetime import datetime

from pydantic import BaseModel, Field


class Address(BaseModel):
    """Physical address information."""
    street: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    postal_code: str | None = None
    formatted: str | None = None


class GeolocationData(BaseModel):
    """Geolocation data from device sensors."""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    accuracy: float | None = Field(None, description="Accuracy in meters")
    altitude: float | None = Field(None, description="Altitude in meters")
    altitude_accuracy: float | None = None
    heading: float | None = Field(None, ge=0, le=360, description="Direction of travel in degrees from north")
    speed: float | None = Field(None, description="Speed in meters per second")
    timestamp: int
    address: Address | None = None


class DeviceInfo(BaseModel):
    """Device information."""
    platform: str | None = None
    os_version: str | None = None
    browser: str | None = None
    screen_width: int | None = None
    screen_height: int | None = None
    pixel_ratio: float | None = None
    language: str | None = None
    timezone: str | None = None
    battery_level: float | None = Field(None, ge=0, le=1)
    battery_charging: bool | None = None
    network_type: str | None = Field(None, pattern="^(wifi|cellular|ethernet|none)$")
    connection_speed: str | None = Field(None, pattern="^(slow-2g|2g|3g|4g|5g)$")


class WeatherData(BaseModel):
    """Weather information."""
    condition: str | None = None
    temperature: float | None = None
    feels_like: float | None = None
    wind_speed: float | None = None
    wind_direction: int | None = Field(None, ge=0, le=360)


class EnvironmentData(BaseModel):
    """Environmental sensor data."""
    ambient_light: float | None = Field(None, description="Ambient light in lux")
    ambient_noise: float | None = Field(None, description="Ambient noise in decibels")
    temperature: float | None = Field(None, description="Temperature in Celsius")
    humidity: float | None = Field(None, ge=0, le=100)
    pressure: float | None = Field(None, description="Atmospheric pressure in hPa")
    weather: WeatherData | None = None


class ActivityData(BaseModel):
    """User activity information."""
    current_url: str | None = None
    page_title: str | None = None
    session_duration: int | None = Field(None, description="Session duration in milliseconds")
    idle_time: int | None = Field(None, description="Idle time in milliseconds")
    activity_type: str | None = Field(None, pattern="^(stationary|walking|running|automotive|cycling|unknown)$")
    confidence: float | None = Field(None, ge=0, le=1)
    is_active_tab: bool | None = None
    media_playing: bool | None = None


class PersonaEnvironment(BaseModel):
    reported_at: datetime = datetime.now()
    geolocation: GeolocationData | None
    device_info: DeviceInfo | None
    physical_environment: EnvironmentData | None
    user_activity: ActivityData | None
