from datetime import datetime
from typing import Annotated

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.config import settings
from app.utils.alias import validate_custom_alias


class CreateUrlRequest(BaseModel):
    long_url: Annotated[AnyHttpUrl, Field(description="Original URL to shorten")]
    custom_alias: Annotated[
        str | None,
        Field(default=None, description="Optional custom alias"),
    ] = None
    ttl_seconds: Annotated[
        int | None,
        Field(
            default=None,
            description="Link lifetime in seconds; omit for no expiry unless a default is configured",
            ge=1,
        ),
    ] = None

    @field_validator("custom_alias")
    @classmethod
    def validate_alias(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_custom_alias(value)

    @model_validator(mode="after")
    def validate_ttl(self) -> "CreateUrlRequest":
        if self.ttl_seconds is None:
            return self
        if self.ttl_seconds > settings.max_link_ttl_seconds:
            raise ValueError(
                f"ttl_seconds must be at most {settings.max_link_ttl_seconds} seconds"
            )
        return self


class UrlMetadataResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    alias: str
    long_url: str
    short_url: str
    access_count: int
    created_at: datetime
    expires_at: datetime | None = None


class CreateUrlResponse(UrlMetadataResponse):
    pass


class RedirectPreviewResponse(BaseModel):
    alias: str
    redirect_url: str
    status_code: int = 307


class ErrorResponse(BaseModel):
    detail: str
