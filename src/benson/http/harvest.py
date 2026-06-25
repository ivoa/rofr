"""Harvest validation HTTP surface (legacy servlet-compatible query model)."""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request, Response
from lxml import etree
from urllib.parse import quote_plus

from benson.config import Settings
from benson.http import json_compat
from benson.service import harvest_runner
from benson.service.validation_job import spawn_harvest_validation
from benson.session.store import HarvestRun, store

logger = logging.getLogger("benson.http.harvest")

router = APIRouter(prefix="/registry-validate", tags=["registry-validate"])


def merge_query_params(params: Any) -> dict[str, str]:
    buckets: defaultdict[str, list[str]] = defaultdict(list)
    for k, raw in params.multi_items():
        buckets[k].append(str(raw))
    return {k: (" ".join(v) if len(v) > 1 else v[0]) for k, v in buckets.items()}


def show_default(q: dict[str, str]) -> str:
    return q.get("show") or "fail warn rec"


def new_run_from_query(q: dict[str, str], endpoint: str) -> HarvestRun:
    return HarvestRun(
        run_id=f"{uuid.uuid4().hex}.tmp",
        endpoint=endpoint,
        builtin_schemas="builtinSchemas" in q,
        cache=str(q.get("cache", "")).lower() == "true",
        show_status=show_default(q),
        fmt=q.get("format", "html").lower(),
        error_fmt=q.get("errorFormat", "html").lower(),
    )


def format_tree_response(tree: etree._ElementTree | None, fmt: str) -> Response:  # noqa: SLF001
    if tree is None:
        return Response(status_code=204)

    root = tree.getroot()
    data = etree.tostring(root, encoding="UTF-8", xml_declaration=True, pretty_print=True)
    if fmt == "xml":
        return Response(content=data, media_type="application/xml")
    if fmt == "text":
        return Response(content=data, media_type="text/plain; charset=utf-8")

    escaped = data.decode(errors="replace").replace("&", "&amp;").replace("<", "&lt;")
    html = (
        "<!DOCTYPE html><html><head><meta charset='utf-8'/>"
        "<title>Benson Harvest</title></head><body><pre>"
        f"{escaped}"
        "</pre></body></html>"
    )
    return Response(content=html.encode(), media_type="text/html")


@router.api_route("/harvest", methods=["GET", "POST"])
async def harvest_validater(request: Request) -> Response:
    settings: Settings = request.app.state.settings
    client: httpx.AsyncClient = request.app.state.http_client
    q = merge_query_params(request.query_params)
    run_id = q.get("runid")
    endpoint_raw = q.get("endpoint")
    op_raw = q.get("op")
    op = op_raw.lower() if isinstance(op_raw, str) else None

    parity_json = settings.parity_json_quotes or q.get("errorFormat", "").lower() == "json"
    fmt = q.get("format", "html").lower()

    def pseudo_json(payload: dict | list) -> Response:
        s = json_compat.response_json(parity_json, payload)
        return Response(content=s.encode(), media_type="application/json")

    sess_cookie = request.cookies.get("JSESSIONID") or uuid.uuid4().hex.upper()

    if not run_id:
        if not endpoint_raw:
            raise HTTPException(status_code=400, detail="Missing arguments: endpoint")
        run = new_run_from_query(q, endpoint_raw)
        await store.create(run)
        run_id = run.run_id

    run = await store.get(run_id)
    if run is None:
        raise HTTPException(status_code=409, detail="Session unavailable")

    if run.canceled and op not in (None, "startsession", "getstatus", "cancel"):
        raise HTTPException(status_code=409, detail="Canceled")

    if op == "startsession":
        base = str(request.base_url).rstrip("/")
        ep_q = quote_plus(run.endpoint)
        sess_url = f"{base}/api/v1/registry-validate/harvest?runid={run.run_id}&endpoint={ep_q}&"
        resp = pseudo_json({"status": "ready", "sessionURL": sess_url})
        resp.set_cookie("JSESSIONID", sess_cookie, path="/")
        return resp

    if op == "getstatus":
        rows = list(run.status_rows)
        if not rows:
            rows.append(
                {
                    "id": run.run_id,
                    "ok": "true",
                    "message": "idle",
                    "done": "false",
                    "status": "waiting",
                },
            )
        resp = pseudo_json(rows)
        resp.set_cookie("JSESSIONID", sess_cookie, path="/")
        return resp

    if op == "register":
        from benson.registry.registration import RegistrationError, register_publisher

        oid = (q.get("oai_identifier") or q.get("identifier") or "").strip()
        title = (q.get("title") or "").strip()
        if not oid or not title:
            raise HTTPException(
                status_code=400,
                detail="Register requires oai_identifier and title query parameters.",
            )
        try:
            result = await register_publisher(
                run.run_id,
                oai_identifier=oid,
                title=title,
                settings=settings,
            )
        except RegistrationError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
        return pseudo_json(
            {
                "status": "ok",
                "created": result.created,
                "oai_identifier": result.record.oai_identifier,
                "title": result.record.title,
                "harvest_access_url": result.record.harvest_access_url,
                "updated_at": result.record.updated_at,
            }
        )

    if op == "cancel":
        run.canceled = True
        if run.background_task and not run.background_task.done():
            run.background_task.cancel()
        return pseudo_json({"status": "canceled"})

    if op == "getresource":
        rid = q.get("id")
        if not rid or rid not in run.resources:
            raise HTTPException(status_code=400, detail="Unknown id")
        blob = run.resources[rid]
        if fmt == "xml":
            return Response(content=blob, media_type="application/xml")
        return Response(content=blob, media_type="application/octet-stream")

    if op == "validateresource":
        rid = q.get("id")
        if not rid or rid not in run.resources:
            raise HTTPException(status_code=400, detail="Unknown id")
        sub = {rid: run.resources[rid]}
        vor_root, _stats = harvest_runner.phase3_validate_only(sub, run.show_status, run.builtin_schemas, settings)
        r = format_tree_response(etree.ElementTree(vor_root), fmt)
        r.set_cookie("JSESSIONID", sess_cookie, path="/")
        return r

    if op == "validateoai":
        try:
            tree = await harvest_runner.validate_oai_only(run, settings, client)
        except Exception as exc:
            logger.exception("ValidateOAI failed run_id=%s", run.run_id)
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        r = format_tree_response(tree, fmt)
        r.set_cookie("JSESSIONID", sess_cookie, path="/")
        return r

    if op == "validateivoa":
        try:
            tree = await harvest_runner.validate_ivoa_only(run, settings, client)
        except Exception as exc:
            logger.exception("ValidateIVOA failed run_id=%s", run.run_id)
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        r = format_tree_response(tree, fmt)
        r.set_cookie("JSESSIONID", sess_cookie, path="/")
        return r

    if op == "validatevor":
        cap = 5 if not run.cache else 1
        try:
            tree = await harvest_runner.validate_vor_only(run, settings, client, max_records=cap)
        except Exception as exc:
            logger.exception("ValidateVOR failed run_id=%s", run.run_id)
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        r = format_tree_response(tree, fmt)
        r.set_cookie("JSESSIONID", sess_cookie, path="/")
        return r

    if op == "validate" or op is None:
        if run.cache:
            spawn_harvest_validation(
                run,
                settings=settings,
                client=client,
                max_records=1,
            )
            base_u = str(request.base_url).rstrip("/")
            result_url = f"{base_u}/api/v1/registry-validate/harvest?runid={run.run_id}&op=Validate&format={quote_plus(fmt)}"
            out = pseudo_json({"status": "running", "resultURL": result_url})
            out.set_cookie("JSESSIONID", sess_cookie, path="/")
            return out

        try:
            merged, _vor = await harvest_runner.execute_harvest_validation(
                run,
                settings=settings,
                client=client,
                max_records=5,
            )
            _ = _vor
        except Exception as exc:
            logger.exception("Validate (sync) failed run_id=%s", run.run_id)
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        r = format_tree_response(merged, fmt)
        r.set_cookie("JSESSIONID", sess_cookie, path="/")
        return r

    raise HTTPException(status_code=400, detail=f"Unknown op {op_raw!r}")
