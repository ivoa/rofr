"""OAI-PMH endpoint for the IVOA standards catalog."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import Response

from benson.oai.catalog import load_publisher_oai_records
from benson.oai.server import OAI_XML_MEDIA_TYPE, dispatch_oai_verb, parse_oai_request_params
from benson.registry.standards_store import StandardsStore

router = APIRouter(tags=["oai"])


@router.api_route("/oai", methods=["GET", "POST"], name="oai")
async def oai_endpoint(request: Request) -> Response:
    settings = request.app.state.settings
    store = StandardsStore.from_settings(settings)
    publisher_records = await load_publisher_oai_records(settings)
    base_url = str(request.url_for("oai"))
    raw = await parse_oai_request_params(request)
    body = dispatch_oai_verb(
        settings,
        store,
        base_url,
        raw,
        publisher_records=publisher_records,
    )
    return Response(content=body, media_type=OAI_XML_MEDIA_TYPE)
