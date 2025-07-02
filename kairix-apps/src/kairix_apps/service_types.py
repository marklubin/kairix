from kairix_core.types.environmental_context import ActivityData, DeviceInfo, EnvironmentData, GeolocationData
from pydantic import BaseModel, Field


class ContextUpdateRequest(BaseModel):
    """Request body for context update endpoint."""
    timestamp: int = Field(..., description="Unix timestamp in milliseconds")
    session_id: str = Field(..., description="Unique session identifier")
    device_id: str | None = Field(None, description="Unique device identifier")
    geolocation: GeolocationData | None = None
    device: DeviceInfo | None = None
    environment: EnvironmentData | None = None
    activity: ActivityData | None = None

class ContextUpdateResponse(BaseModel):
    """Response body for context update endpoint."""
    success: bool
    message: str
