"""FastAPI handlers that log exceptions before returning responses."""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import Request
from fastapi.exception_handlers import http_exception_handler as default_http_exc_handler
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from starlette.responses import Response

log = logging.getLogger("benson.http")


def _path(request: Request) -> str:
    try:
        return request.url.path
    except Exception:
        return str(request.scope.get("path", ""))


def _extra(request: Request) -> str:
    try:
        rid = request.query_params.get("runid")
        return f" runid={rid}" if rid else ""
    except Exception:
        return ""


async def logged_http_exception_handler(request: Request, exc: HTTPException) -> Response:
    """Ensure 4xx/5xx HTTPException bodies are visible in logs (not only uvicorn generic line)."""
    detail: Any = exc.detail
    if isinstance(detail, (list, dict)):
        detail_repr = repr(detail)[:800]
    else:
        detail_repr = str(detail)[:2000]

    path = _path(request)
    extra = _extra(request)
    msg = "%s %s -> HTTP %s | %s%s"

    args = (
        request.method,
        path,
        exc.status_code,
        detail_repr,
        extra,
    )
    if exc.status_code >= 500:
        log.error(msg, *args)
    else:
        log.warning(msg, *args)

    return await default_http_exc_handler(request, exc)


async def logged_unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Log full traceback when an error is not surfaced as HTTPException."""
    log.exception("%s %s — unhandled exception", request.method, _path(request))

    payload: dict[str, str] = {"detail": "Internal server error"}
    if os.environ.get("BENSON_EXPOSE_ERRORS", "").lower() in ("1", "true", "yes"):
        payload["detail"] = str(exc)[:2000]
    return JSONResponse(status_code=500, content=payload)
