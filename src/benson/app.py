"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI

from benson.logging_setup import configure_logging
from benson.config import Settings
from benson.http.error_handlers import (
    logged_http_exception_handler,
    logged_unhandled_exception_handler,
)
from benson.http import harvest as harvest_routes
from benson.http import home as home_routes
from benson.http import oai as oai_routes
from benson.http import publishers as publishers_routes
from benson.http import validator as validator_routes
from benson.http import vor as vor_routes
from benson.http.web import configure_web
from starlette.exceptions import HTTPException


def fastapi_app(asgi_app: Any) -> FastAPI:
    """Return the FastAPI instance (unwrap ``ProxyHeadersMiddleware`` if present)."""
    while hasattr(asgi_app, "app"):
        asgi_app = asgi_app.app
    return asgi_app


def _wrap_proxy_headers(app: Any, settings: Settings) -> Any:
    """Apply X-Forwarded-Proto/Host so ``request.url_for`` and templates match the public URL."""
    from benson.http.proxy_middleware import wrap_proxy_middleware

    return wrap_proxy_middleware(
        app,
        trusted_hosts=settings.forwarded_allow_ips,
        enabled=settings.proxy_headers,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    settings = Settings.from_env()
    app.state.settings = settings
    configure_web(app, settings)
    async with httpx.AsyncClient(http2=False) as client:
        app.state.http_client = client
        yield


def create_app() -> FastAPI:
    settings = Settings.from_env()
    application = FastAPI(title="Benson Registry Validate", lifespan=lifespan)
    application.state.settings = settings
    configure_web(application, settings)
    application.add_exception_handler(HTTPException, logged_http_exception_handler)
    application.add_exception_handler(Exception, logged_unhandled_exception_handler)
    application.include_router(home_routes.router)
    application.include_router(oai_routes.router)
    application.include_router(validator_routes.router)
    application.include_router(publishers_routes.router, prefix="/api/v1")
    application.include_router(harvest_routes.router, prefix="/api/v1")
    application.include_router(vor_routes.router, prefix="/api/v1")
    return _wrap_proxy_headers(application, settings)


app = create_app()
