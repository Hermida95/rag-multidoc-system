from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging, get_logger
from app.core.rate_limit import BlanketRateLimitMiddleware, limiter

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)

# Upstream provider errors (502s from OpenAI) can carry raw error text from
# the provider. Log it in full server-side, but never forward it verbatim to
# API clients — it may describe internal request details that aren't ours
# to disclose to whoever holds a valid API key.
_GENERIC_UPSTREAM_ERROR_MESSAGE = (
    "Upstream AI provider request failed. Please try again shortly."
)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description=(
            "Production-ready Multi-Document RAG system: upload PDFs/Markdown, "
            "index them with semantic chunking + embeddings, and query them "
            "with cited, grounded answers."
        ),
        version="1.0.0",
        debug=settings.debug,
    )

    if not settings.api_key:
        logger.warning(
            "api_key_unset",
            hint=(
                "API_KEY is empty — /documents and /chat endpoints are "
                "unauthenticated. Fine for local dev, never for a "
                "deployment reachable by anyone else."
            ),
        )

    app.state.limiter = limiter
    # slowapi's handler signature predates Starlette's typed ExceptionHandler
    # protocol; functionally correct, just not typed to match it yet.
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
    # Blanket per-IP limit at the ASGI layer, ahead of routing/dependencies —
    # covers failed-auth requests that never reach a per-endpoint
    # @limiter.limit(...) decorator. See core/rate_limit.py for why this
    # isn't slowapi's own SlowAPIMiddleware.
    app.add_middleware(
        BlanketRateLimitMiddleware,
        max_requests=settings.blanket_rate_limit_per_minute,
        window_seconds=60,
    )

    if settings.cors_origins_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins_list,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        logger.warning(
            "app_error",
            error_code=exc.error_code,
            message=exc.message,
            path=request.url.path,
        )
        client_message = (
            _GENERIC_UPSTREAM_ERROR_MESSAGE if exc.status_code >= 500 else exc.message
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"error_code": exc.error_code, "message": client_message},
        )

    return app


app = create_app()
