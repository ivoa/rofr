"""Public catalog endpoints for RofR lists."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response

from benson.oai.catalog import load_publisher_oai_records
from benson.oai.server import OAI_XML_MEDIA_TYPE, dispatch_oai_verb
from benson.registry.publishers_store import PublisherStore
from benson.registry.standards_store import StandardsStore

router = APIRouter(tags=["catalog"])

_LIST_PUBLISHERS_QUERY = {
    "verb": ["ListRecords"],
    "metadataPrefix": ["ivo_vor"],
    "set": ["ivo_publishers"],
}


@router.get("/list-publishers", name="list_publishers")
async def list_publishers(request: Request) -> Response:
    """Legacy ListRecords view of registered publishers (full OAI-PMH envelope)."""
    settings = request.app.state.settings
    await PublisherStore.from_settings(settings).ensure_seed()
    store = StandardsStore.from_settings(settings)
    publisher_records = await load_publisher_oai_records(settings)
    base_url = str(request.url_for("list_publishers"))
    body = dispatch_oai_verb(
        settings,
        store,
        base_url,
        _LIST_PUBLISHERS_QUERY,
        publisher_records=publisher_records,
    )
    return Response(content=body, media_type=OAI_XML_MEDIA_TYPE)


@router.get("/list-searchables", response_class=HTMLResponse, include_in_schema=False)
async def list_searchables_stub() -> HTMLResponse:
    """Reserved; searchables are loaded on the home page from RegTAP/cache today."""
    return HTMLResponse(
        "<p>Searchables catalog is not exposed here yet. Use the home page or RegTAP sync.</p>",
        status_code=501,
    )
