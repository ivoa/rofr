"""Publishing registry JSON API and registration."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from benson.registry.registration import RegistrationError, eligibility_payload, register_publisher
from benson.registry.publishers_store import PublisherStore
from benson.session.store import store

router = APIRouter(prefix="/registry", tags=["publishers"])


class RegisterBody(BaseModel):
    run_id: str
    oai_identifier: str
    title: str


def _publisher_json(rec) -> dict:
    return {
        "oai_identifier": rec.oai_identifier,
        "title": rec.title,
        "harvest_access_url": rec.harvest_access_url,
        "registered_at": rec.registered_at,
        "updated_at": rec.updated_at,
        "validation_run_id": rec.validation_run_id,
        "last_checked_at": rec.last_checked_at,
        "check_status": rec.check_status,
        "live_oai_identifier": rec.live_oai_identifier,
        "live_title": rec.live_title,
        "check_detail": rec.check_detail,
    }


@router.get("/publishers")
async def list_publishers_json(request: Request) -> JSONResponse:
    settings = request.app.state.settings
    pub_store = PublisherStore.from_settings(settings)
    await pub_store.ensure_seed()
    records = await pub_store.load()
    return JSONResponse([_publisher_json(r) for r in records])


@router.get("/publishers/eligibility/{run_id}")
async def registration_eligibility(run_id: str, request: Request) -> JSONResponse:
    settings = request.app.state.settings
    run = await store.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Validation session not found")
    return JSONResponse(await eligibility_payload(run, settings))


@router.post("/publishers")
async def register_publisher_api(body: RegisterBody, request: Request) -> JSONResponse:
    settings = request.app.state.settings
    try:
        result = await register_publisher(
            body.run_id,
            oai_identifier=body.oai_identifier,
            title=body.title,
            settings=settings,
        )
    except RegistrationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    payload = _publisher_json(result.record)
    payload["created"] = result.created
    status_code = 201 if result.created else 200
    return JSONResponse(payload, status_code=status_code)
