import time
import uuid
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.logging import correlation_id_ctx, logger


class RequestIDMiddleware:
    """Middleware to ensure every request has an X-Request-ID header and context variable."""
    
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = None
        for name, value in scope.get("headers", []):
            if name.lower() == b"x-request-id":
                request_id = value.decode("utf-8").strip()
                break
        
        if not request_id:
            request_id = str(uuid.uuid4())

        # Set in scope for FastAPI request.state
        if "state" not in scope:
            scope["state"] = {}
        scope["state"]["request_id"] = request_id

        token = correlation_id_ctx.set(request_id)
        
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                # Create a new list of headers to avoid mutating the original in place if needed
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode("utf-8")))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            correlation_id_ctx.reset(token)


class TimingAndLoggingMiddleware:
    """Middleware to measure request processing duration and log structured request/response summary."""
    
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.perf_counter()
        path = scope["path"]
        method = scope["method"]

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                duration_ms = (time.perf_counter() - start_time) * 1000
                status_code = message["status"]
                
                headers = list(message.get("headers", []))
                headers.append((b"x-process-time-ms", f"{duration_ms:.2f}".encode("utf-8")))
                message["headers"] = headers

                if status_code >= 400:
                    logger.warning(f"{method} {path} - {status_code} ({duration_ms:.2f}ms)")
                else:
                    logger.info(f"{method} {path} - {status_code} ({duration_ms:.2f}ms)")
            
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"{method} {path} - FAILED ({duration_ms:.2f}ms) with error: {str(exc)}")
            raise exc
