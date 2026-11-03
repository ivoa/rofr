# ADR 0003: FastAPI, Starlette, and uvicorn for HTTP

## Status

Accepted

## Context

Benson must expose many **HTTP routes**: HTML forms and job UI, JSON status APIs, multipart VOR uploads, OAI-PMH XML responses, static assets, and Jinja templates. The legacy system used servlets; the rewrite needs an ASGI-capable stack that supports async outbound HTTP (harvesting registries) and straightforward testing.

Alternatives considered implicitly include Flask (WSGI, less natural async integration), Django (heavier than needed for a focused validator service), and raw Starlette alone (more boilerplate for routing and request parsing).

## Decision

Use **FastAPI** on **Starlette** with **uvicorn** as the production ASGI server:

| Layer | Role in Benson |
|-------|----------------|
| **FastAPI** | Application factory (`create_app`), APIRouter modules under `benson.http`, form/multipart handling, exception handlers |
| **Starlette** | ASGI foundation, `Jinja2Templates`, static files, `HTTPException`; custom proxy middleware for forwarded headers |
| **uvicorn** | Served via `benson` CLI and Docker entrypoint; `--factory` loads `benson.app:create_app` |

Implementation notes:

- One shared **`httpx.AsyncClient`** is created in the app **lifespan** for outbound OAI and HTTP GET tests.
- **Proxy headers** (`BENSON_PROXY_HEADERS`, uvicorn `ProxyHeadersMiddleware`, and `X-Forwarded-Host` handling) ensure `request.url_for` and templates match the public URL behind reverse proxies.
- Tests use **`httpx.ASGITransport`** against the app without binding a port.

## Consequences

- **Positive:** Clear module-per-area routing (`validator`, `harvest`, `oai`, `vor`, …), async-friendly harvest jobs, and a well-documented deployment path in the project README.
- **Positive:** FastAPI’s request types align with multipart VOR validation and JSON job APIs.
- **Negative:** Middleware wrapping (proxy headers) requires helpers like `fastapi_app()` to unwrap the inner FastAPI instance in tests.
- **Neutral:** OpenAPI auto-docs are not a product requirement; routes are defined for parity with legacy paths, not primarily for public API discovery.
