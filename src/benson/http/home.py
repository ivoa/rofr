"""Registry of Registries landing page."""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from starlette.templating import Jinja2Templates

from benson.config import Settings
from benson.service.rofr_lists import (
    load_publishers,
    render_publishers_section,
    render_searchables_section,
)
from benson.service.searchables_regtap import load_searchables

logger = logging.getLogger("benson.http.home")

router = APIRouter(tags=["home"])

_ROFR_NOTE = "https://www.ivoa.net/documents/Notes/RegistryOfRegistries/index.html"
_REG_IF = "https://www.ivoa.net/documents/RegistryInterface/index.html"
_GETTING_IN = "https://www.ivoa.net/twiki/bin/view/IVOA/GettingIntoTheRegistry"
_RESREG = "https://www.ivoa.net/twiki/bin/view/IVOA/IvoaResReg"


def _register_href(_settings: Settings) -> str:
    return "/validator"


def _templates(request: Request) -> Jinja2Templates:
    return request.app.state.templates


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def home(request: Request) -> HTMLResponse:
    settings: Settings = request.app.state.settings
    client: httpx.AsyncClient = request.app.state.http_client
    searchables_warn: str | None = None
    publishers_warn: str | None = None
    searchables_body: str
    publishers_body: str

    try:
        s = await load_searchables(
            client,
            settings,
            timeout_sec=min(60.0, settings.harvest_timeout_sec),
        )
        searchables_body = render_searchables_section(s)
    except Exception as e:  # noqa: BLE001 — show friendly surface; log detail
        logger.warning("searchables fetch failed: %s", e)
        searchables_warn = f"{type(e).__name__}"
        searchables_body = (
            '<p class="muted">This list could not be loaded. Please try again later.</p>'
        )

    try:
        p = await load_publishers(
            settings,
            client,
            str(request.base_url).rstrip("/"),
        )
        publishers_body = render_publishers_section(p)
    except Exception as e:  # noqa: BLE001
        logger.warning("publishers fetch failed: %s", e)
        publishers_warn = f"{type(e).__name__}"
        publishers_body = '<p class="muted">This list could not be loaded. Please try again later.</p>'

    return _templates(request).TemplateResponse(
        request,
        "home.html",
        {
            "register_href": _register_href(settings),
            "rofr_note_url": _ROFR_NOTE,
            "getting_in_url": _GETTING_IN,
            "resreg_url": _RESREG,
            "reg_if_url": _REG_IF,
            "publishers_catalog_path": (
                "/oai?verb=ListRecords&metadataPrefix=ivo_vor&set=ivo_publishers"
            ),
            "searchables_body": searchables_body,
            "publishers_body": publishers_body,
            "searchables_warn": searchables_warn,
            "publishers_warn": publishers_warn,
        },
    )
