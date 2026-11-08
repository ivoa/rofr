"""Probe registered publishers via OAI Identify."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
from lxml import etree

from benson.oai.client import fetch_oai
from benson.oai.phase2 import RI_NS, XSI_NS, extract_identify_state
from benson.oai.phase2 import OAI_NS
from benson.registry.publishers_store import PublisherStore, normalize_endpoint
from benson.service.rofr_lists import PublisherRegistry, harvest_access_url_from_metadata

_XPATH_NS = {"oai": OAI_NS, "ri": RI_NS, "xsi": XSI_NS}

@dataclass
class PublisherCheckResult:
    oai_identifier: str
    harvest_access_url: str | None
    status: str
    live_oai_identifier: str | None
    live_title: str | None
    detail: str | None
    checked_at: str


def _find_registry_element(parsed: etree._Element) -> etree._Element | None:  # noqa: SLF001
    regs = parsed.xpath(
        ".//oai:Identify/oai:description/ri:Resource[contains(@xsi:type, ':Registry')]",
        namespaces=_XPATH_NS,
    )
    return regs[0] if regs else None


def _result(
    pub: PublisherRegistry,
    *,
    status: str,
    checked_at: str,
    live_oai_identifier: str | None = None,
    live_title: str | None = None,
    detail: str | None = None,
) -> PublisherCheckResult:
    return PublisherCheckResult(
        oai_identifier=pub.oai_identifier,
        harvest_access_url=pub.harvest_access_url,
        status=status,
        live_oai_identifier=live_oai_identifier,
        live_title=live_title,
        detail=detail,
        checked_at=checked_at,
    )


async def _check_one(
    client: httpx.AsyncClient,
    pub: PublisherRegistry,
    *,
    timeout: float,
    checked_at: str,
) -> PublisherCheckResult:
    url = pub.harvest_access_url
    if not url:
        return _result(
            pub,
            status="no_endpoint",
            checked_at=checked_at,
            detail="No harvest_access_url stored",
        )

    try:
        status, raw, codes, parse_err = await fetch_oai(
            client, url, "verb=Identify", timeout=timeout
        )
    except httpx.HTTPError as exc:
        return _result(
            pub,
            status="unreachable",
            checked_at=checked_at,
            detail=str(exc),
        )

    if not 200 <= status < 300:
        return _result(
            pub,
            status="unreachable",
            checked_at=checked_at,
            detail=f"HTTP {status}",
        )

    if parse_err:
        return _result(
            pub,
            status="invalid_response",
            checked_at=checked_at,
            detail=parse_err,
        )

    if codes:
        return _result(
            pub,
            status="invalid_response",
            checked_at=checked_at,
            detail=f"OAI error: {', '.join(sorted(codes))}",
        )

    try:
        parsed = etree.fromstring(raw, etree.XMLParser(no_network=True, resolve_entities=False))
    except etree.XMLSyntaxError as exc:
        return _result(
            pub,
            status="invalid_response",
            checked_at=checked_at,
            detail=str(exc),
        )

    reg_elem = _find_registry_element(parsed)
    if reg_elem is None:
        return _result(
            pub,
            status="no_registry",
            checked_at=checked_at,
            detail="Identify response has no vg:Registry in description",
        )

    state = extract_identify_state(parsed)
    live_id = (state.get("registrationIdentifier") or "").strip() or None
    live_title = (state.get("registrationTitle") or "").strip() or None

    detail_parts: list[str] = []
    live_harvest = harvest_access_url_from_metadata(reg_elem)
    if live_harvest and normalize_endpoint(live_harvest) != normalize_endpoint(url):
        detail_parts.append(f"live harvest URL is {live_harvest}")

    if not live_id:
        return _result(
            pub,
            status="no_registry",
            checked_at=checked_at,
            detail="vg:Registry found but no identifier",
            live_title=live_title,
        )

    if live_id != pub.oai_identifier:
        mismatch_detail = f"live identifier is {live_id}"
        if detail_parts:
            mismatch_detail = f"{mismatch_detail}; {'; '.join(detail_parts)}"
        return _result(
            pub,
            status="identifier_mismatch",
            checked_at=checked_at,
            live_oai_identifier=live_id,
            live_title=live_title,
            detail=mismatch_detail,
        )

    return _result(
        pub,
        status="ok",
        checked_at=checked_at,
        live_oai_identifier=live_id,
        live_title=live_title,
        detail="; ".join(detail_parts) if detail_parts else None,
    )


async def check_publishers(
    client: httpx.AsyncClient,
    store: PublisherStore,
    *,
    timeout: float,
    concurrency: int = 5,
) -> list[PublisherCheckResult]:
    publishers = await store.load()
    checked_at = datetime.now(timezone.utc).isoformat()
    sem = asyncio.Semaphore(max(1, concurrency))

    async def run(pub: PublisherRegistry) -> PublisherCheckResult:
        async with sem:
            return await _check_one(client, pub, timeout=timeout, checked_at=checked_at)

    return list(await asyncio.gather(*(run(p) for p in publishers)))
