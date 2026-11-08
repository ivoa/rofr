"""OAI-PMH 2.0 server for the Benson standards registry."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

from lxml import etree

from benson.config import Settings
from benson.oai.dates import earliest_datestamp, record_in_range, validate_from_until
from benson.oai.oai_dc import resource_to_oai_dc
from benson.oai.resumption import ResumptionState, decode_token, encode_token
from benson.registry.publisher_oai import IVO_PUBLISHERS
from benson.registry.standards_store import StandardRecord, StandardsStore

OAI_NS = "http://www.openarchives.org/OAI/2.0/"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
OAI_XML_MEDIA_TYPE = "text/xml; charset=utf-8"

IVO_MANAGED = "ivo_managed"
KNOWN_SETS = frozenset({IVO_MANAGED, IVO_PUBLISHERS})
METADATA_FORMATS: dict[str, tuple[str, str]] = {
    "ivo_vor": (
        "http://www.ivoa.net/xml/VOResource/v1.0",
        "http://www.ivoa.net/xml/VOResource/v1.0",
    ),
    "oai_dc": (
        "http://www.openarchives.org/OAI/2.0/oai_dc/",
        "http://www.openarchives.org/OAI/2.0/oai_dc/oai_dc.xsd",
    ),
}

ALLOWED_VERBS = frozenset(
    {"Identify", "ListMetadataFormats", "ListSets", "ListIdentifiers", "ListRecords", "GetRecord"}
)


def _response_date() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _request_url(base_url: str, params: dict[str, str]) -> str:
    base = base_url.rstrip("?&")
    if not params:
        return base
    return f"{base}?{urlencode(params)}"


def _oai_root() -> etree._Element:
    return etree.Element(
        f"{{{OAI_NS}}}OAI-PMH",
        nsmap={
            "oai": OAI_NS,
            "xsi": XSI_NS,
        },
        attrib={
            f"{{{XSI_NS}}}schemaLocation": (
                f"{OAI_NS} https://www.openarchives.org/OAI/2.0/OAI-PMH.xsd"
            ),
        },
    )


def _prepend_envelope(root: etree._Element, base_url: str, req_params: dict[str, str]) -> None:
    rd = etree.Element(f"{{{OAI_NS}}}responseDate")
    rd.text = _response_date()
    req = etree.Element(f"{{{OAI_NS}}}request")
    for key, value in req_params.items():
        req.set(key, value)
    req.text = _request_url(base_url, req_params)
    root.insert(0, req)
    root.insert(0, rd)


def _emit(root: etree._Element, base_url: str, req_params: dict[str, str]) -> bytes:
    _prepend_envelope(root, base_url, req_params)
    return etree.tostring(root, encoding="UTF-8", xml_declaration=True, pretty_print=True)


def oai_error(
    code: str,
    message: str,
    base_url: str,
    req_params: dict[str, str],
) -> bytes:
    root = _oai_root()
    err = etree.SubElement(root, f"{{{OAI_NS}}}error", code=code)
    err.text = message
    return _emit(root, base_url, req_params)


def _duplicate_keys(raw: dict[str, list[str]], keys: frozenset[str]) -> bool:
    return any(len(raw[k]) > 1 for k in keys if k in raw)


def _first(raw: dict[str, list[str]], key: str) -> str | None:
    vals = raw.get(key)
    if not vals:
        return None
    return vals[0]


def _req_params_for(raw: dict[str, list[str]]) -> dict[str, str]:
    return {k: v[0] for k, v in raw.items() if v}


def _managed_records(store: StandardsStore, settings: Settings, base_url: str) -> list[StandardRecord]:
    return store.all_records(settings, base_url)


def _filter_records(
    records: list[StandardRecord],
    *,
    from_raw: str | None,
    until_raw: str | None,
) -> list[StandardRecord]:
    out: list[StandardRecord] = []
    for rec in records:
        if rec.resource_status == "deleted":
            out.append(rec)
            continue
        if not record_in_range(rec.datestamp, from_raw, until_raw):
            continue
        out.append(rec)
    return out


def _list_pool(
    store: StandardsStore,
    settings: Settings,
    base_url: str,
    publisher_records: list[StandardRecord],
    set_spec: str | None,
) -> list[StandardRecord]:
    if set_spec == IVO_PUBLISHERS:
        return list(publisher_records)
    if set_spec == IVO_MANAGED or set_spec is None:
        return _managed_records(store, settings, base_url)
    return []


def _lookup_record(
    store: StandardsStore,
    settings: Settings,
    base_url: str,
    identifier: str,
    publisher_records: list[StandardRecord],
) -> StandardRecord | None:
    ident = identifier.strip()
    rec = store.get_by_identifier(settings, base_url, ident)
    if rec is not None:
        return rec
    for pub in publisher_records:
        if pub.identifier == ident:
            return pub
    return None


def _set_specs_for_record(rec: StandardRecord, request_set: str | None) -> tuple[str, ...]:
    if request_set is not None:
        return (request_set,)
    return (rec.oai_set,)


def _append_header(
    parent: etree._Element,
    rec: StandardRecord,
    *,
    set_specs: tuple[str, ...] = (),
) -> None:  # noqa: SLF001
    header = etree.SubElement(parent, f"{{{OAI_NS}}}header")
    if rec.resource_status == "deleted":
        header.set("status", "deleted")
    ident = etree.SubElement(header, f"{{{OAI_NS}}}identifier")
    ident.text = rec.identifier
    ds = etree.SubElement(header, f"{{{OAI_NS}}}datestamp")
    ds.text = rec.datestamp
    for spec in set_specs:
        set_el = etree.SubElement(header, f"{{{OAI_NS}}}setSpec")
        set_el.text = spec


def _append_metadata(parent: etree._Element, rec: StandardRecord, metadata_prefix: str) -> None:  # noqa: SLF001
    if rec.resource_status == "deleted":
        return
    md = etree.SubElement(parent, f"{{{OAI_NS}}}metadata")
    if metadata_prefix == "ivo_vor":
        md.append(
            etree.fromstring(
                etree.tostring(rec.metadata, encoding="UTF-8"),
                parser=etree.XMLParser(no_network=True, resolve_entities=False),
            )
        )
    elif metadata_prefix == "oai_dc":
        md.append(resource_to_oai_dc(rec.metadata))


def _paginate(
    records: list[StandardRecord],
    cursor: int,
    page_size: int,
) -> tuple[list[StandardRecord], int | None]:
    page = records[cursor : cursor + page_size]
    next_cursor = cursor + page_size
    if next_cursor >= len(records):
        return page, None
    return page, next_cursor


def _handle_identify(
    settings: Settings,
    store: StandardsStore,
    base_url: str,
    raw: dict[str, list[str]],
    *,
    publisher_records: list[StandardRecord],
) -> bytes:
    req = _req_params_for(raw)
    if _first(raw, "verb") != "Identify" or set(raw.keys()) != {"verb"}:
        return oai_error("badArgument", "Illegal argument", base_url, req)

    records = _managed_records(store, settings, base_url) + publisher_records
    ds_list = [r.datestamp for r in records]

    root = _oai_root()
    identify = etree.SubElement(root, f"{{{OAI_NS}}}Identify")
    for tag, text in (
        ("repositoryName", settings.oai_repository_name),
        ("baseURL", base_url.rstrip("?&")),
        ("protocolVersion", "2.0"),
        ("adminEmail", settings.oai_admin_email),
        ("earliestDatestamp", earliest_datestamp(ds_list)),
        ("deletedRecord", "persistent"),
        ("granularity", "YYYY-MM-DDThh:mm:ssZ"),
    ):
        el = etree.SubElement(identify, f"{{{OAI_NS}}}{tag}")
        el.text = text

    from benson.registry.registry_self import build_registry_resource

    description = etree.SubElement(identify, f"{{{OAI_NS}}}description")
    description.append(build_registry_resource(base_url, settings))
    return _emit(root, base_url, req)


def _handle_list_metadata_formats(
    settings: Settings,
    store: StandardsStore,
    base_url: str,
    raw: dict[str, list[str]],
    *,
    publisher_records: list[StandardRecord],
) -> bytes:
    req = _req_params_for(raw)
    ident = _first(raw, "identifier")
    if ident is not None:
        if _lookup_record(store, settings, base_url, ident, publisher_records) is None:
            return oai_error("idDoesNotExist", "Unknown identifier", base_url, req)

    root = _oai_root()
    lmf = etree.SubElement(root, f"{{{OAI_NS}}}ListMetadataFormats")
    for prefix, (schema, namespace) in METADATA_FORMATS.items():
        mf = etree.SubElement(lmf, f"{{{OAI_NS}}}metadataFormat")
        p = etree.SubElement(mf, f"{{{OAI_NS}}}metadataPrefix")
        p.text = prefix
        sch = etree.SubElement(mf, f"{{{OAI_NS}}}schema")
        sch.text = schema
        ns = etree.SubElement(mf, f"{{{OAI_NS}}}metadataNamespace")
        ns.text = namespace
    return _emit(root, base_url, req)


def _handle_list_sets(base_url: str, raw: dict[str, list[str]]) -> bytes:
    req = _req_params_for(raw)
    root = _oai_root()
    ls = etree.SubElement(root, f"{{{OAI_NS}}}ListSets")
    for set_spec, set_name in (
        (IVO_MANAGED, "Records originating at this registry"),
        (IVO_PUBLISHERS, "Registered publishing registries known to the RofR"),
    ):
        s = etree.SubElement(ls, f"{{{OAI_NS}}}set")
        spec = etree.SubElement(s, f"{{{OAI_NS}}}setSpec")
        spec.text = set_spec
        name = etree.SubElement(s, f"{{{OAI_NS}}}setName")
        name.text = set_name
    return _emit(root, base_url, req)


def _validate_list_args(
    raw: dict[str, list[str]],
    base_url: str,
    *,
    require_metadata_prefix: bool,
) -> tuple[dict[str, str], str | None, ResumptionState | None]:
    """Return (req_params, error_code, resumed_state)."""
    req = _req_params_for(raw)

    if _duplicate_keys(raw, frozenset({"metadataPrefix", "resumptionToken", "set", "from", "until"})):
        return req, "badArgument", None

    token = _first(raw, "resumptionToken")
    if token is not None:
        state = decode_token(token)
        if state is None:
            return req, "badResumptionToken", None
        return req, None, state

    if require_metadata_prefix:
        mdp = _first(raw, "metadataPrefix")
        if mdp is None:
            return req, "badArgument", None
        if mdp not in METADATA_FORMATS:
            return req, "cannotDisseminateFormat", None

    set_spec = _first(raw, "set")
    if set_spec is not None and set_spec not in KNOWN_SETS:
        return req, "noSetHierarchy", None

    from_raw = _first(raw, "from")
    until_raw = _first(raw, "until")
    date_err = validate_from_until(from_raw, until_raw)
    if date_err:
        return req, date_err, None

    if until_raw is not None:
        from benson.oai.dates import parse_oai_date

        up = parse_oai_date(until_raw)
        if up and up.instant.year < 1970:
            return req, "noRecordsMatch", None

    return req, None, None


def _list_state_from_raw(raw: dict[str, list[str]], verb: str) -> ResumptionState:
    return ResumptionState(
        verb=verb,
        metadata_prefix=_first(raw, "metadataPrefix") or "",
        set_spec=_first(raw, "set"),
        from_raw=_first(raw, "from"),
        until_raw=_first(raw, "until"),
        cursor=0,
    )


def _handle_list_identifiers(
    settings: Settings,
    store: StandardsStore,
    base_url: str,
    raw: dict[str, list[str]],
    *,
    publisher_records: list[StandardRecord],
) -> bytes:
    req, err, resumed = _validate_list_args(raw, base_url, require_metadata_prefix=True)
    if err:
        msg = {
            "badResumptionToken": "Invalid resumption token",
            "cannotDisseminateFormat": "Unknown metadata prefix",
            "noSetHierarchy": "Unknown set",
            "noRecordsMatch": "No records match",
        }.get(err, "Illegal argument")
        return oai_error(err, msg, base_url, req)

    state = resumed or _list_state_from_raw(raw, "ListIdentifiers")
    if state.metadata_prefix not in METADATA_FORMATS:
        return oai_error("cannotDisseminateFormat", "Unknown metadata prefix", base_url, req)

    pool = _list_pool(store, settings, base_url, publisher_records, state.set_spec)
    filtered = _filter_records(
        pool,
        from_raw=state.from_raw,
        until_raw=state.until_raw,
    )
    page, next_cursor = _paginate(filtered, state.cursor, settings.oai_max_records)

    if not page and state.cursor == 0:
        return oai_error("noRecordsMatch", "No records match", base_url, req)

    root = _oai_root()
    li = etree.SubElement(root, f"{{{OAI_NS}}}ListIdentifiers")
    for rec in page:
        oai_rec = etree.SubElement(li, f"{{{OAI_NS}}}record")
        _append_header(oai_rec, rec, set_specs=_set_specs_for_record(rec, state.set_spec))

    if next_cursor is not None:
        next_state = ResumptionState(
            verb=state.verb,
            metadata_prefix=state.metadata_prefix,
            set_spec=state.set_spec,
            from_raw=state.from_raw,
            until_raw=state.until_raw,
            cursor=next_cursor,
        )
        rt = etree.SubElement(li, f"{{{OAI_NS}}}resumptionToken")
        rt.text = encode_token(next_state)
        rt.set("completeListSize", str(len(filtered)))
        rt.set("cursor", str(next_cursor))

    emit_req = req if resumed is None else {
        "verb": "ListIdentifiers",
        "resumptionToken": _first(raw, "resumptionToken") or "",
    }
    return _emit(root, base_url, emit_req)


def _handle_list_records(
    settings: Settings,
    store: StandardsStore,
    base_url: str,
    raw: dict[str, list[str]],
    *,
    publisher_records: list[StandardRecord],
) -> bytes:
    req, err, resumed = _validate_list_args(raw, base_url, require_metadata_prefix=True)
    if err:
        msg = {
            "badResumptionToken": "Invalid resumption token",
            "cannotDisseminateFormat": "Unknown metadata prefix",
            "noSetHierarchy": "Unknown set",
            "noRecordsMatch": "No records match",
        }.get(err, "Illegal argument")
        return oai_error(err, msg, base_url, req)

    state = resumed or _list_state_from_raw(raw, "ListRecords")
    if state.metadata_prefix not in METADATA_FORMATS:
        return oai_error("cannotDisseminateFormat", "Unknown metadata prefix", base_url, req)

    pool = _list_pool(store, settings, base_url, publisher_records, state.set_spec)
    filtered = _filter_records(
        pool,
        from_raw=state.from_raw,
        until_raw=state.until_raw,
    )
    page, next_cursor = _paginate(filtered, state.cursor, settings.oai_max_records)

    if not page and state.cursor == 0:
        return oai_error("noRecordsMatch", "No records match", base_url, req)

    root = _oai_root()
    lr = etree.SubElement(root, f"{{{OAI_NS}}}ListRecords")
    for rec in page:
        oai_rec = etree.SubElement(lr, f"{{{OAI_NS}}}record")
        _append_header(oai_rec, rec, set_specs=_set_specs_for_record(rec, state.set_spec))
        _append_metadata(oai_rec, rec, state.metadata_prefix)

    if next_cursor is not None:
        next_state = ResumptionState(
            verb=state.verb,
            metadata_prefix=state.metadata_prefix,
            set_spec=state.set_spec,
            from_raw=state.from_raw,
            until_raw=state.until_raw,
            cursor=next_cursor,
        )
        rt = etree.SubElement(lr, f"{{{OAI_NS}}}resumptionToken")
        rt.text = encode_token(next_state)
        rt.set("completeListSize", str(len(filtered)))
        rt.set("cursor", str(next_cursor))

    emit_req = req if resumed is None else {
        "verb": "ListRecords",
        "resumptionToken": _first(raw, "resumptionToken") or "",
    }
    return _emit(root, base_url, emit_req)


def _handle_get_record(
    settings: Settings,
    store: StandardsStore,
    base_url: str,
    raw: dict[str, list[str]],
    *,
    publisher_records: list[StandardRecord],
) -> bytes:
    req = _req_params_for(raw)
    if _duplicate_keys(raw, frozenset({"metadataPrefix", "identifier"})):
        return oai_error("badArgument", "Illegal argument", base_url, req)

    ident = _first(raw, "identifier")
    mdp = _first(raw, "metadataPrefix")
    if ident is None or mdp is None:
        return oai_error("badArgument", "Missing identifier or metadataPrefix", base_url, req)
    if mdp not in METADATA_FORMATS:
        return oai_error("cannotDisseminateFormat", "Unknown metadata prefix", base_url, req)

    rec = _lookup_record(store, settings, base_url, ident, publisher_records)
    if rec is None:
        return oai_error("idDoesNotExist", "Unknown identifier", base_url, req)

    root = _oai_root()
    gr = etree.SubElement(root, f"{{{OAI_NS}}}GetRecord")
    oai_rec = etree.SubElement(gr, f"{{{OAI_NS}}}record")
    _append_header(oai_rec, rec, set_specs=_set_specs_for_record(rec, None))
    _append_metadata(oai_rec, rec, mdp)
    return _emit(root, base_url, req)


def dispatch_oai_verb(
    settings: Settings,
    store: StandardsStore,
    base_url: str,
    raw: dict[str, list[str]],
    *,
    publisher_records: list[StandardRecord] | None = None,
) -> bytes:
    """Build an OAI-PMH XML response for the given query parameters."""
    verb = _first(raw, "verb")
    req = _req_params_for(raw)

    if verb is None:
        return oai_error("badVerb", "Missing verb argument", base_url, req)
    if verb not in ALLOWED_VERBS:
        return oai_error("badVerb", f"Unknown verb {verb!r}", base_url, req)

    pubs = publisher_records if publisher_records is not None else []

    if verb == "Identify":
        return _handle_identify(settings, store, base_url, raw, publisher_records=pubs)
    if verb == "ListMetadataFormats":
        return _handle_list_metadata_formats(
            settings, store, base_url, raw, publisher_records=pubs
        )
    if verb == "ListSets":
        return _handle_list_sets(base_url, raw)
    if verb == "ListIdentifiers":
        return _handle_list_identifiers(
            settings, store, base_url, raw, publisher_records=pubs
        )
    if verb == "ListRecords":
        return _handle_list_records(settings, store, base_url, raw, publisher_records=pubs)
    if verb == "GetRecord":
        return _handle_get_record(settings, store, base_url, raw, publisher_records=pubs)

    return oai_error("badVerb", f"Unknown verb {verb!r}", base_url, req)


def parse_query_params(query: Any) -> dict[str, list[str]]:
    """Normalize Starlette/FastAPI query params to a multimap."""
    out: dict[str, list[str]] = {}
    if hasattr(query, "multi_items"):
        for key, value in query.multi_items():
            out.setdefault(key, []).append(value)
        return out
    for key, value in query.items():
        out.setdefault(key, []).append(str(value))
    return out


async def parse_oai_request_params(request: Any) -> dict[str, list[str]]:
    """OAI query string (GET) or form body (POST)."""
    if request.method == "POST":
        form = await request.form()
        out: dict[str, list[str]] = {}
        for key, value in form.multi_items():
            out.setdefault(key, []).append(str(value))
        return out
    return parse_query_params(request.query_params)
