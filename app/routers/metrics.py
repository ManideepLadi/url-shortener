from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from fastapi import APIRouter
from fastapi.responses import Response

from app.config import settings

metrics_router = APIRouter(tags=["metrics"])


@metrics_router.get(
    "/metrics",
    summary="Prometheus metrics",
    response_class=Response,
    include_in_schema=settings.metrics_enabled,
)
async def prometheus_metrics() -> Response:
    if not settings.metrics_enabled:
        return Response(status_code=404, content="Metrics disabled")
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
