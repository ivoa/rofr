"""Browser-facing registry harvest validator."""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.templating import Jinja2Templates

from benson.http.harvest import new_run_from_query
from benson.http.validation_report import render_validation_report
from benson.registry.registration import (
    RegistrationError,
    eligibility_payload,
    register_publisher,
)
from benson.service.validation_job import spawn_harvest_validation, status_payload
from benson.session.store import HarvestRun, store

logger = logging.getLogger("benson.http.validator")

router = APIRouter(tags=["validator"])


def _templates(request: Request) -> Jinja2Templates:
    return request.app.state.templates


def _validator_page(
    request: Request,
    *,
    endpoint: str = "",
    builtin_schemas: bool = True,
    result_html: str | None = None,
    error: str | None = None,
    watch_run_id: str | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    return _templates(request).TemplateResponse(
        request,
        "validator.html",
        {
            "endpoint": endpoint,
            "builtin_schemas": builtin_schemas,
            "result_html": result_html,
            "error": error,
            "watch_run_id": watch_run_id,
        },
        status_code=status_code,
    )


def _new_run(endpoint: str, *, builtin_schemas: bool) -> HarvestRun:
    q: dict[str, str] = {"format": "html", "show": "fail warn rec", "cache": "true"}
    if builtin_schemas:
        q["builtinSchemas"] = "y"
    return new_run_from_query(q, endpoint)


async def _start_job(request: Request, endpoint: str, *, builtin_schemas: bool):
    settings = request.app.state.settings
    client: httpx.AsyncClient = request.app.state.http_client
    run = _new_run(endpoint, builtin_schemas=builtin_schemas)
    await store.create(run)
    spawn_harvest_validation(run, settings=settings, client=client, max_records=5)
    return run


@router.get("/validator", response_class=HTMLResponse, include_in_schema=False)
@router.get("/regvalidate", response_class=HTMLResponse, include_in_schema=False)
async def validator_form(request: Request, run_id: str | None = None) -> HTMLResponse:
    if run_id:
        run = await store.get(run_id)
        if run is None:
            return _validator_page(
                request,
                error="Validation session not found or expired.",
                status_code=404,
            )
        return _validator_page(
            request,
            endpoint=run.endpoint,
            builtin_schemas=run.builtin_schemas,
            watch_run_id=run_id,
        )
    return _validator_page(request)


@router.post("/validator/jobs")
async def validator_create_job(
    request: Request,
    endpoint: str = Form(...),
    builtin_schemas: bool = Form(False),
) -> JSONResponse:
    endpoint = endpoint.strip()
    if not endpoint:
        raise HTTPException(status_code=400, detail="Enter an OAI-PMH endpoint URL.")
    run = await _start_job(request, endpoint, builtin_schemas=builtin_schemas)
    payload = status_payload(run)
    payload["status_url"] = f"/validator/jobs/{run.run_id}"
    return JSONResponse(payload, status_code=202)


@router.get("/validator/jobs/{run_id}")
async def validator_job_status(run_id: str) -> JSONResponse:
    run = await store.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Validation session not found")
    return JSONResponse(status_payload(run))


@router.get("/validator/jobs/{run_id}/eligibility")
async def validator_job_eligibility(run_id: str, request: Request) -> JSONResponse:
    settings = request.app.state.settings
    run = await store.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Validation session not found")
    return JSONResponse(await eligibility_payload(run, settings))


@router.post("/validator/jobs/{run_id}/register")
async def validator_job_register(
    run_id: str,
    request: Request,
    oai_identifier: str = Form(...),
    title: str = Form(...),
) -> JSONResponse:
    settings = request.app.state.settings
    try:
        result = await register_publisher(
            run_id,
            oai_identifier=oai_identifier,
            title=title,
            settings=settings,
        )
    except RegistrationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    status_code = 201 if result.created else 200
    return JSONResponse(
        {
            "created": result.created,
            "oai_identifier": result.record.oai_identifier,
            "title": result.record.title,
            "harvest_access_url": result.record.harvest_access_url,
            "updated_at": result.record.updated_at,
        },
        status_code=status_code,
    )


@router.get("/validator/jobs/{run_id}/result", response_class=HTMLResponse)
async def validator_job_result(run_id: str) -> HTMLResponse:
    run = await store.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Validation session not found")
    if run.validation_error and run.merged_validation is None:
        raise HTTPException(status_code=500, detail=run.validation_error)
    if run.merged_validation is None:
        raise HTTPException(status_code=409, detail="Validation still running")
    return HTMLResponse(render_validation_report(run.merged_validation))


@router.post("/validator", response_class=HTMLResponse, include_in_schema=False)
@router.post("/regvalidate", response_class=HTMLResponse, include_in_schema=False)
async def validator_submit(
    request: Request,
    endpoint: str = Form(...),
    builtin_schemas: bool = Form(False),
) -> HTMLResponse:
    """Start validation and return immediately with a watchable progress UI."""
    endpoint = endpoint.strip()
    if not endpoint:
        return _validator_page(
            request,
            endpoint="",
            builtin_schemas=builtin_schemas,
            error="Enter an OAI-PMH endpoint URL.",
            status_code=400,
        )
    run = await _start_job(request, endpoint, builtin_schemas=builtin_schemas)
    return _validator_page(
        request,
        endpoint=endpoint,
        builtin_schemas=builtin_schemas,
        watch_run_id=run.run_id,
        status_code=202,
    )
