import logging

from fastapi import APIRouter, Depends, status
from fastapi.responses import RedirectResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.dependencies import get_url_service
from app.schemas.url import CreateUrlRequest, CreateUrlResponse, UrlMetadataResponse
from app.services.url_service import UrlService

logger = logging.getLogger(__name__)

api_router = APIRouter(tags=["urls"])


@api_router.post(
    "/urls",
    response_model=CreateUrlResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a shortened URL",
)
async def create_url(
    body: CreateUrlRequest,
    service: UrlService = Depends(get_url_service),
) -> CreateUrlResponse:
    return await service.create_short_url(body)


@api_router.get(
    "/urls/{alias}",
    response_model=UrlMetadataResponse,
    summary="Get metadata for a shortened URL",
)
async def get_url_metadata(
    alias: str,
    service: UrlService = Depends(get_url_service),
) -> UrlMetadataResponse:
    return await service.get_metadata(alias)


redirect_router = APIRouter(tags=["redirect"])


@redirect_router.get(
    "/{alias}",
    summary="Redirect to the original URL",
    response_class=RedirectResponse,
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
)
async def redirect_to_long_url(
    alias: str,
    service: UrlService = Depends(get_url_service),
) -> RedirectResponse:
    long_url = await service.resolve_redirect(alias)
    return RedirectResponse(url=long_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


health_router = APIRouter(tags=["health"])


@health_router.get("/health", summary="Health check")
async def health_check(
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    db_status = "ok"

    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Database health check failed")
        db_status = "error"

    overall = "ok" if db_status == "ok" else "degraded"
    return {
        "status": overall,
        "database": db_status,
        "cache": "in-memory",
    }
