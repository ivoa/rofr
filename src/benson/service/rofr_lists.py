"""Fetch and parse RofR publisher-registry list from a catalogue base URL."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import TYPE_CHECKING, Any

import httpx
from lxml import etree

if TYPE_CHECKING:
    from benson.config import Settings

OAI_NS = "http://www.openarchives.org/OAI/2.0/"


@dataclass(slots=True)
class SearchableRegistry:
    title: str
    href: str | None
    fields: dict[str, str]


@dataclass(slots=True)
class PublisherRegistry:
    oai_identifier: str
    title: str
    harvest_access_url: str | None
    registered_at: str | None = None
    updated_at: str | None = None
    validation_run_id: str | None = None
    last_checked_at: str | None = None
    check_status: str | None = None
    live_oai_identifier: str | None = None
    live_title: str | None = None
    check_detail: str | None = None


LIST_PUBLISHERS_PATH = "/list-publishers"


def _local(tag: str) -> str:
    return f"*[local-name()='{tag}']"


def _local_tag(tag: object) -> str:
    if not isinstance(tag, str):
        return ""
    if tag.startswith("{"):
        return tag.partition("}")[2]
    return tag


def harvest_access_url_from_metadata(metadata: Any) -> str | None:
    """First OAI harvest accessURL under a Registry capability."""
    for cap in metadata.iter():
        if _local_tag(cap.tag) != "capability":
            continue
        sid = (cap.attrib.get("standardID") or "").lower()
        if "ivo://ivoa.net/std/registry" not in sid:
            continue
        for elem in cap.iter():
            if _local_tag(elem.tag) == "accessURL":
                u = (elem.text or "").strip()
                if u:
                    return u
    return None


def parse_publishers_oai(content: bytes) -> list[PublisherRegistry]:
    root = etree.fromstring(content)
    ns = {"oai": OAI_NS}
    records = root.xpath("//oai:record", namespaces=ns)
    out: list[PublisherRegistry] = []
    for rec in records:
        oid_el = rec.xpath("string(oai:header/oai:identifier)", namespaces=ns)
        oai_id = (oid_el or "").strip()
        meta = rec.find(f"{{{OAI_NS}}}metadata")
        if meta is None or len(meta) == 0:
            continue
        res = meta[0]
        title_el = res.xpath(_local("title"))
        title = (title_el[0].text or "").strip() if title_el else ""
        harvest = harvest_access_url_from_metadata(res)
        if oai_id:
            out.append(
                PublisherRegistry(
                    oai_identifier=oai_id,
                    title=title or oai_id,
                    harvest_access_url=harvest,
                )
            )
    return out


async def load_publishers(settings: Settings, client: httpx.AsyncClient, origin: str) -> list[PublisherRegistry]:
    """Load publishers from local JSON registry or remote JSON API."""
    from benson.registry.publishers_store import PublisherStore  # noqa: PLC0415

    store = PublisherStore.from_settings(settings)
    if settings.publishers_registry_file.is_file():
        return await store.load()
    url = f"{origin.rstrip('/')}/api/v1/registry/publishers"
    r = await client.get(url, timeout=min(120.0, settings.harvest_timeout_sec))
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list):
        return []
    out: list[PublisherRegistry] = []
    for row in data:
        if not isinstance(row, dict):
            continue
        oid = (row.get("oai_identifier") or "").strip()
        if not oid:
            continue
        out.append(
            PublisherRegistry(
                oai_identifier=oid,
                title=(row.get("title") or "").strip() or oid,
                harvest_access_url=(row.get("harvest_access_url") or "").strip() or None,
                registered_at=row.get("registered_at"),
                validation_run_id=row.get("validation_run_id"),
                last_checked_at=row.get("last_checked_at"),
                check_status=row.get("check_status"),
                live_oai_identifier=row.get("live_oai_identifier"),
                live_title=row.get("live_title"),
                check_detail=row.get("check_detail"),
            )
        )
    return out


async def fetch_publishers(
    client: httpx.AsyncClient,
    origin: str,
    *,
    timeout_sec: float = 120.0,
    settings: Settings | None = None,
) -> list[PublisherRegistry]:
    if settings is not None:
        return await load_publishers(settings, client, origin)
    url = f"{origin.rstrip('/')}{LIST_PUBLISHERS_PATH}"
    r = await client.get(url, timeout=timeout_sec)
    r.raise_for_status()
    return parse_publishers_oai(r.content)


def format_utc_display(iso: str) -> str:
    """Format an ISO-8601 UTC timestamp for UI display with an explicit UTC suffix."""
    s = iso.strip()
    if s.endswith("+00:00"):
        s = s[:-6] + "Z"
    return f"{s} UTC"


def render_searchables_section(entries: list[SearchableRegistry]) -> str:
    if not entries:
        return "<p class=\"muted\">No searchable registries were returned.</p>"
    parts: list[str] = ['<ul class="registry-cards">']
    for e in entries:
        title = escape(e.title)
        link = escape(e.href) if e.href else None
        head = f'<a href="{link}" rel="noopener noreferrer">{title}</a>' if link else title
        fli = "".join(
            f'<li><span class="k">{escape(k)}</span> {escape(v)}</li>'
            for k, v in e.fields.items()
        )
        parts.append(f'<li class="registry-card"><h3 class="card-title">{head}</h3><ul class="fields">{fli}</ul></li>')
    parts.append("</ul>")
    return "".join(parts)


def render_publishers_section(entries: list[PublisherRegistry]) -> str:
    if not entries:
        return "<p class=\"muted\">No publishing registries were returned.</p>"
    parts: list[str] = ['<ul class="registry-cards">']
    for e in entries:
        hid = escape(e.oai_identifier)
        t = escape(e.title)
        ou = escape(e.harvest_access_url) if e.harvest_access_url else None
        harvest = (
            f'<p class="harvest"><span class="k">OAI-PMH endpoint</span> '
            f'<a href="{ou}" rel="noopener noreferrer">{ou}</a></p>'
            if ou
            else ""
        )
        check_meta = ""
        if e.last_checked_at:
            ts = escape(format_utc_display(e.last_checked_at))
            status = escape(e.check_status or "unknown")
            status_class = "warn" if e.check_status and e.check_status != "ok" else "muted"
            check_meta = (
                f'<p class="last-checked {status_class}">'
                f'<span class="k">Last check</span> {status} · {ts}</p>'
            )
            if e.check_detail and e.check_status != "ok":
                check_meta += f'<p class="check-detail warn">{escape(e.check_detail)}</p>'
        parts.append(
            f'<li class="registry-card"><h3 class="card-title">{t}</h3>'
            f'<p class="id"><span class="k">IVOA Identifier</span> <code>{hid}</code></p>'
            f"{harvest}{check_meta}</li>"
        )
    parts.append("</ul>")
    return "".join(parts)
