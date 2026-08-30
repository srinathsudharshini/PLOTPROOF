import time
import uuid
from collections import defaultdict
from typing import Callable, Dict, List
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Applies production security headers to all responses (Layer 10, Section 17).
    """
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data: https:; script-src 'self' 'unsafe-inline'; object-src 'none'"
        return response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Injects traceable X-Request-ID across all requests (Layer 10, Section 24).
    """
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        req_id = request.headers.get("X-Request-ID", f"req-{uuid.uuid4().hex[:12]}")
        request.state.request_id = req_id
        start_time = time.time()

        response = await call_next(request)

        duration_ms = int((time.time() - start_time) * 1000)
        response.headers["X-Request-ID"] = req_id
        response.headers["X-Response-Time-Ms"] = str(duration_ms)
        return response


class InMemoryRateLimiter:
    """
    In-memory sliding window rate limiter differentiating standard vs CPU-heavy endpoints (Layer 10, Section 18 & 19).
    """
    def __init__(self, default_limit: int = 120, heavy_limit: int = 20, window_seconds: int = 60):
        self.default_limit = default_limit
        self.heavy_limit = heavy_limit
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, client_ip: str, path: str) -> bool:
        now = time.time()
        window_start = now - self.window_seconds
        key = f"{client_ip}:{path}"

        # Clean old timestamps
        self.requests[key] = [t for t in self.requests[key] if t > window_start]

        # Heavy / Sensitive endpoints: OCR, ZK prove, large uploads, authentication attempts
        is_heavy = any(h in path for h in ["/privacy/prove", "/ocr", "/upload", "/auth/login"])
        limit = self.heavy_limit if is_heavy else self.default_limit

        if len(self.requests[key]) >= limit:
            return False

        self.requests[key].append(now)
        return True


rate_limiter = InMemoryRateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware protecting against DoS and credential stuffing (Layer 10, Section 18).
    """
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host if request.client else "127.0.0.1"
        path = request.url.path

        # Bypass rate limits for health and testing endpoints
        if path in ["/health", "/ready", "/api/health", "/docs", "/openapi.json"]:
            return await call_next(request)

        if not rate_limiter.is_allowed(client_ip, path):
            return JSONResponse(
                status_code=429,
                content={
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": "Too many requests. Please try again later.",
                },
                headers={"Retry-After": "60"},
            )

        return await call_next(request)
