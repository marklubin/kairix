"""User data models."""


from pydantic import BaseModel, Field


class User(BaseModel):
    """Represents a Kairix user."""

    subdomain: str = Field(..., min_length=3, max_length=3, pattern="^[a-z0-9]{3}$")
    password_hash: str
    web_port: int = Field(..., ge=1024, le=65535)
    api_port: int = Field(..., ge=1024, le=65535)
    tools_port: int = Field(..., ge=1024, le=65535)
    enabled: bool = True

    model_config = {"validate_assignment": True}


class UserConfig(BaseModel):
    """Configuration for a user instance."""

    username: str
    user: User
    sqlite_path: str
    environment: dict[str, str] = Field(default_factory=dict)
