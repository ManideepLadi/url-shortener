import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.middleware.logging import RequestLoggingMiddleware
from app.routers.urls import api_router, health_router, redirect_router
from app.utils.exceptions import AppError

# ---------------------------------------------------------------------------
# PostgreSQL startup/shutdown (disabled for local dev — uncomment when ready)
# ---------------------------------------------------------------------------
# from app.db.session import close_db, init_db

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Starting %s in %s mode (in-memory storage — no PostgreSQL/Redis)",
        settings.app_name,
        settings.app_env,
    )
    # await init_db()
    yield
    # await close_db()
    logger.info("Shutdown complete")


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)

app.include_router(health_router)
app.include_router(api_router, prefix="/api/v1")
# Redirect route registered last so it does not shadow /api or /health.
app.include_router(redirect_router)


@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    logger.warning("Application error: %s", exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )


@app.exception_handler(ValueError)
async def validation_error_handler(_request: Request, exc: ValueError) -> JSONResponse:
    logger.warning("Validation error: %s", exc)
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc)},
    )
