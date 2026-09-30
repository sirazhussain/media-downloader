"""FastAPI application factory."""

from __future__ import annotations

import time

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import health, media
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.security import MediaDownloaderError
from app.schemas.media import ErrorResponse

logger = get_logger(__name__)


def _error_payload(code: str, message: str) -> dict:
    return ErrorResponse.model_validate(
        {"error": {"code": code, "message": message}}
    ).model_dump()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/api/docs",
        redoc_url=None,
    )

    if "*" in settings.cors_origins:
        logger.warning("CORS allows all origins; restrict this in production.")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition"],
    )

    @app.middleware("http")
    async def request_logging(request: Request, call_next):  # type: ignore[no-untyped-def]
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        # Path only: never log full user-supplied URLs or query strings.
        logger.info(
            "request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response

    @app.exception_handler(MediaDownloaderError)
    async def app_error_handler(request: Request, exc: MediaDownloaderError) -> JSONResponse:
        logger.info(
            "request failed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": exc.status_code,
                "error_code": exc.code,
            },
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(exc.code, exc.message),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_error_payload("INVALID_REQUEST", "The request payload is invalid."),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        # Never leak tracebacks, paths, or internals to the client.
        logger.exception(
            "unhandled error",
            extra={"method": request.method, "path": request.url.path},
        )
        return JSONResponse(
            status_code=500,
            content=_error_payload("INTERNAL_ERROR", "An unexpected error occurred."),
        )

    app.include_router(health.router, prefix="/api/v1")
    app.include_router(media.router, prefix="/api/v1")

    return app


app = create_app()
