from datetime import datetime
from typing import Annotated

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator

from app.utils.alias import validate_custom_alias


class CreateUrlRequest(BaseModel):
    long_url: Annotated[AnyHttpUrl, Field(description="Original URL to shorten")]
    custom_alias: Annotated[
        str | None,
        Field(default=None, description="Optional custom alias"),
    ] = None

    @field_validator("custom_alias")
    @classmethod
    def validate_alias(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_custom_alias(value)


class UrlMetadataResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    alias: str
    long_url: str
    short_url: str
    access_count: int
    created_at: datetime


class CreateUrlResponse(UrlMetadataResponse):
    pass


class RedirectPreviewResponse(BaseModel):
    alias: str
    redirect_url: str
    status_code: int = 307


class ErrorResponse(BaseModel):
    detail: str
