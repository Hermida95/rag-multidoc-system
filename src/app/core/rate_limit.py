import time
from collections import defaultdict, deque

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

# Per-endpoint limits, e.g. @limiter.limit(settings.rate_limit_query) on the
# /chat/query handler. These wrap the endpoint function itself, so they only
# run once the function executes — i.e. *after* the verify_api_key
# dependency has already accepted the request. They do NOT cover
# failed-auth requests; see BlanketRateLimitMiddleware below for that.
limiter = Limiter(key_func=get_remote_address)


class BlanketRateLimitMiddleware(BaseHTTPMiddleware):
    """Per-IP fixed-window limit applied to every request, before routing or
    dependency resolution.

    Deliberately NOT implemented with slowapi's own SlowAPIMiddleware: that
    middleware resolves the target handler by walking `app.routes` and
    matching each route's `.matches()`, which assumes every route is a
    flattened, introspectable APIRoute. Newer FastAPI versions register
    included routers as an opaque, lazily-resolved wrapper instead, so that
    walk finds no handler, treats the route as exempt, and silently applies
    no limit at all — a shared-secret endpoint would look protected in the
    code while actually being wide open. This middleware only needs
    `request.client.host`, so it has no such dependency and can't regress
    silently the same way if the framework's internals change again.

    In-memory and per-process by design: fine for a single API instance
    (the deployment target here). It would need a shared store (Redis, the
    same one Celery already uses) to stay correct if scaled to multiple
    processes/instances, since each would otherwise count independently.
    """

    def __init__(self, app, max_requests: int, window_seconds: int = 60) -> None:
        super().__init__(app)
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        hits = self._hits[client_ip]

        while hits and now - hits[0] > self._window_seconds:
            hits.popleft()

        if len(hits) >= self._max_requests:
            return JSONResponse(
                status_code=429,
                content={
                    "error_code": "rate_limited",
                    "message": "Too many requests, please slow down.",
                },
            )

        hits.append(now)
        return await call_next(request)
