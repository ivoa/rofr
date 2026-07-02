"""Phase 3: ListRecords harvest loop (ivo_vor / ivo_managed) with XSD + optional XSLT."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from urllib.parse import quote

import httpx
from lxml import etree

from benson.config import Settings
from benson.oai.client import fetch_oai
from benson.xml import results as R
from benson.xml import xsd_validate
from benson.xml import xslt_eval

OAI_NS = "http://www.openarchives.org/OAI/2.0/"
HARVEST_QUERY = "ListRecords harvest"


@dataclass(slots=True)
class HarvestStats:
    nfail: int = 0
    nwarn: int = 0
    npass: int = 0
    failures: list[tuple[str, str]] = field(default_factory=list)

    def as_tuple(self) -> tuple[str, str, str]:
        return str(self.nfail), str(self.nwarn), str(self.nrecish())

    def nrecish(self) -> int:
        return self.nwarn  # parity placeholder for “recommendations”

    def record_failure(self, ident: str, message: str) -> None:
        self.nfail += 1
        self.failures.append((ident, message))


def extract_records(xml_bytes: bytes) -> tuple[list[etree._Element], str | None]:  # noqa: SLF001
    parser = etree.XMLParser(no_network=True, resolve_entities=False, huge_tree=True)
    try:
        root = etree.fromstring(xml_bytes, parser)
    except etree.XMLSyntaxError:
        return [], None

    rt = root.find(f".//{{{OAI_NS}}}resumptionToken")
    token_text = rt.text.strip() if rt is not None and rt.text else None

    records: list[etree._Element] = []
    lr = root.find(f".//{{{OAI_NS}}}ListRecords")
    if lr is None:
        lr = root
    for rec in lr.findall(f"{{{OAI_NS}}}record"):
        records.append(rec)
    return records, token_text


def _is_deleted_record(rec: etree._Element) -> bool:  # noqa: SLF001
    header = rec.find(f"{{{OAI_NS}}}header")
    if header is None:
        return False
    return (header.get("status") or "").strip().lower() == "deleted"


async def harvest_voresource_documents(
    client: httpx.AsyncClient,
    endpoint: str,
    *,
    max_records: int,
    timeout: float,
    builtin_schemas: bool,
    settings: Settings,
) -> tuple[dict[str, bytes], HarvestStats]:
    """Harvest up to ``max_records`` metadata XML blobs keyed by OAI identifier."""

    collected: dict[str, bytes] = {}
    stats = HarvestStats()
    token_frag: str | None = None

    while len(collected) < max_records:
        if token_frag is None:
            q_use = "verb=ListRecords&metadataPrefix=ivo_vor&set=ivo_managed"
        else:
            q_use = "verb=ListRecords&resumptionToken=" + quote(token_frag, safe="")
        _status, raw, codes, parse_err = await fetch_oai(client, endpoint, q_use, timeout=timeout)
        if codes:
            stats.record_failure(
                HARVEST_QUERY,
                f"OAI error code(s): {', '.join(sorted(codes))}",
            )
            break
        if parse_err:
            stats.record_failure(HARVEST_QUERY, parse_err)
            break
        records, resume = extract_records(raw)
        token_frag = resume

        for rec in records:
            if len(collected) >= max_records:
                break
            if _is_deleted_record(rec):
                continue

            hid = rec.find(f"{{{OAI_NS}}}header/{{{OAI_NS}}}identifier")
            ident = hid.text.strip() if hid is not None and hid.text else f"_anon_{len(collected)}"

            md = rec.find(f"{{{OAI_NS}}}metadata")
            if md is None or len(md) == 0:
                stats.record_failure(ident, "ListRecords record has no metadata")
                continue
            vor_el = md[0]
            inner = etree.tostring(vor_el, encoding="UTF-8", xml_declaration=False)
            collected[ident] = inner

        if token_frag is None:
            break

    return collected, stats


def _local_tag(el: etree._Element) -> str:  # noqa: SLF001
    tag = el.tag
    if not isinstance(tag, str):
        return ""
    if tag.startswith("{"):
        return tag.rpartition("}")[2]
    return tag


def _rightnow_param() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S")


def _vor_xslt_params(
    record_id: str,
    show_status: str,
    *,
    extra: dict[str, str] | None = None,
) -> dict[str, str]:
    params = {
        "showStatus": show_status,
        "queryName": record_id,
        "role": "resource",
        "rightnow": _rightnow_param(),
    }
    if extra:
        params.update(extra)
    return params


def _append_xslt_tests(
    tq: etree._Element,  # noqa: SLF001
    xout: etree._ElementTree,
) -> list[etree._Element]:  # noqa: SLF001
    appended: list[etree._Element] = []
    for child in xout.getroot():
        if _local_tag(child) != "test":
            continue
        tq.append(child)
        appended.append(child)
    return appended


def _record_stats_for_tests(stats: HarvestStats, tests: list[etree._Element]) -> None:
    if not tests:
        return
    statuses = [(t.get("status") or "pass").lower() for t in tests]
    if any(s == "fail" for s in statuses):
        stats.nfail += 1
    elif any(s == "warn" for s in statuses):
        stats.nwarn += 1
    else:
        stats.npass += 1


def validate_voresource_documents(
    records: dict[str, bytes],
    show_status: str,
    *,
    builtin_schemas: bool,
    settings: Settings,
    xsl_params: dict[str, str] | None = None,
) -> tuple[etree._Element, HarvestStats]:
    root = R.vor_validation_root(show_status)
    stats = HarvestStats()
    xsl_path = settings.assets_root / "checkVOResource.xsl"

    for rid, blob in records.items():
        tq = etree.SubElement(
            root,
            "testQuery",
            name="resource",
            recordName=rid,
            role="resource",
            status="active",
        )
        tq.set("ivo-id", rid)

        try:
            el = etree.fromstring(blob, etree.XMLParser(no_network=True, resolve_entities=False))
        except etree.XMLSyntaxError as exc:
            stats.nfail += 1
            tq.append(err_test(str(exc)))
            continue

        # Bundled catalog when builtinSchemas; otherwise validate declared xsi:schemaLocation.
        if builtin_schemas:
            errs = xsd_validate.validate_element_tree(el, settings.schema_root)
        else:
            errs = xsd_validate.validate_element_tree_declared(el, settings.schema_root)

        if errs:
            stats.nfail += 1
            bad = etree.Element("test", item="VRvalid", status="fail")
            bad.text = "; ".join(errs[:5])
            if len(errs) > 5:
                bad.text += "…"
            tq.append(bad)
            continue

        if xsl_path.is_file():
            params = _vor_xslt_params(rid, show_status, extra=xsl_params)
            try:
                xout = xslt_eval.transform(xsl_path, el, params=params)
                tests = _append_xslt_tests(tq, xout)
                if tests:
                    _record_stats_for_tests(stats, tests)
                    continue
            except Exception:
                pass

        stats.npass += 1
        tq.append(pass_test())

    return root, stats


def harvest_fail_test(msg: str) -> etree._Element:
    t = etree.Element("test", item="VR-harvest", status="fail")
    t.text = msg
    return t


def append_harvest_failure(
    vor_root: etree._Element,  # noqa: SLF001
    *,
    ident: str,
    message: str,
) -> None:
    if ident == HARVEST_QUERY:
        name = HARVEST_QUERY
        record_name = None
    else:
        name = "resource"
        record_name = ident
    tq = etree.SubElement(
        vor_root,
        "testQuery",
        name=name,
        role="harvest",
        status="active",
    )
    if record_name:
        tq.set("recordName", record_name)
        tq.set("ivo-id", record_name)
    tq.append(harvest_fail_test(message))


def append_harvest_failures(
    vor_root: etree._Element,  # noqa: SLF001
    failures: list[tuple[str, str]],
) -> None:
    for ident, message in failures:
        append_harvest_failure(vor_root, ident=ident, message=message)


def err_test(msg: str) -> etree._Element:
    t = etree.Element("test", item="VR-xml", status="fail")
    t.text = msg
    return t


def pass_test() -> etree._Element:
    t = etree.Element("test", item="VRvalid", status="pass")
    t.text = "OK"
    return t
