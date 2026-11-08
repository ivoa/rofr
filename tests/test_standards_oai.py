"""Tests for the /oai standards catalog endpoint."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
import httpx
from lxml import etree

_repo = Path(__file__).resolve().parents[1]
os.environ.setdefault("SCHEMA_ROOT", str(_repo / "assets" / "schemas"))
os.environ.setdefault("ASSETS_ROOT", str(_repo / "assets" / "validate"))
os.environ.setdefault("STANDARDS_DIR", str(_repo / "assets" / "standards"))

from benson.app import create_app, fastapi_app  # noqa: E402
from benson.config import Settings  # noqa: E402
from benson.oai.phase1 import _error_codes_acceptable  # noqa: E402
from benson.oai.phase1_tests_data import OAI_PHASE1_CASES  # noqa: E402
from benson.oai.phase2 import (  # noqa: E402
    IVOA_CHECKS,
    extract_identify_registry_resource_xml,
    extract_identify_state,
    identify_registration_defaults,
)
from benson.oai.phase3 import extract_records  # noqa: E402
from benson.oai.xmlutil import extract_error_codes  # noqa: E402
from benson.registry.standards_store import StandardsStore  # noqa: E402
from benson.xml import xsd_validate  # noqa: E402

OAI_NS = "http://www.openarchives.org/OAI/2.0/"


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    settings = Settings.from_env()
    app = create_app()
    core = fastapi_app(app)
    async with httpx.AsyncClient() as hc:
        core.state.settings = settings
        core.state.http_client = hc
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


def test_extract_identify_state_parses_registry_id() -> None:
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<oai:OAI-PMH xmlns:oai="http://www.openarchives.org/OAI/2.0/"
             xmlns:ri="http://www.ivoa.net/xml/RegistryInterface/v1.0"
             xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <oai:Identify>
    <oai:description>
      <ri:Resource xsi:type="vg:Registry">
        <ri:identifier>ivo://ivoa.net/rofr</ri:identifier>
        <ri:managedAuthority>ivoa.net</ri:managedAuthority>
      </ri:Resource>
    </oai:description>
  </oai:Identify>
</oai:OAI-PMH>"""
    root = etree.fromstring(xml, etree.XMLParser(no_network=True, resolve_entities=False))
    state = extract_identify_state(root)
    assert state["registryID"] == "ivo://ivoa.net/rofr"
    assert state["managedAuthorityIDs"] == "/ivoa.net/"


def test_identify_registration_defaults_from_fixture() -> None:
    fixture = (_repo / "tests" / "fixtures" / "cadc_identify.xml").read_bytes()
    root = etree.fromstring(fixture, etree.XMLParser(no_network=True, resolve_entities=False))
    defaults = identify_registration_defaults(root)
    assert defaults["oai_identifier"] == "ivo://cadc.nrc.ca/registry"
    assert defaults["title"] == "CADC Registry"


def test_extract_identify_registry_resource_xml_from_fixture() -> None:
    fixture = (_repo / "tests" / "fixtures" / "cadc_identify.xml").read_bytes()
    root = etree.fromstring(fixture, etree.XMLParser(no_network=True, resolve_entities=False))
    xml = extract_identify_registry_resource_xml(root)
    assert xml is not None
    assert "ivo://cadc.nrc.ca/registry" in xml
    assert "managedAuthority" in xml
    assert "cadc.nrc.ca" in xml


def test_identify_registration_defaults_repository_name_fallback() -> None:
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<oai:OAI-PMH xmlns:oai="http://www.openarchives.org/OAI/2.0/">
  <oai:Identify>
    <oai:repositoryName>Example Registry</oai:repositoryName>
    <oai:identifier>ivo://example.org/registry</oai:identifier>
  </oai:Identify>
</oai:OAI-PMH>"""
    root = etree.fromstring(xml, etree.XMLParser(no_network=True, resolve_entities=False))
    defaults = identify_registration_defaults(root)
    assert defaults["oai_identifier"] == "ivo://example.org/registry"
    assert defaults["title"] == "Example Registry"


def test_standards_store_loads_adql() -> None:
    settings = Settings.from_env()
    store = StandardsStore.from_settings(settings)
    records = store.standards()
    adql = next(r for r in records if r.identifier == "ivo://ivoa.net/std/ADQL")
    assert adql.datestamp == "2023-05-23T14:03:00Z"
    assert adql.identifier == "ivo://ivoa.net/std/ADQL"
    title = adql.metadata.find(".//{*}title")
    assert title is not None
    assert title.text


def test_all_records_rofr_ordering() -> None:
    settings = Settings.from_env()
    store = StandardsStore.from_settings(settings)
    records = store.all_records(settings, "http://test/oai")
    ids = [r.identifier for r in records]
    assert ids[0] == "ivo://ivoa.net/rofr"
    assert ids[1] == "ivo://ivoa.net"
    assert ids[2] == "ivo://ivoa.net/IVOA"
    first_std = next(i for i, ident in enumerate(ids) if ident.startswith("ivo://ivoa.net/std/"))
    assert first_std == 3
    assert ids[first_std:] == sorted(ids[first_std:])


@pytest.mark.asyncio
async def test_phase2_ivoa_gets(client: AsyncClient) -> None:
    for _role, qp in IVOA_CHECKS:
        r = await client.get(f"/oai?{qp}")
        assert r.status_code == 200
        root = etree.fromstring(r.content, etree.XMLParser(no_network=True, resolve_entities=False))
        assert not extract_error_codes(root), r.text[:500]
    lr = await client.get("/oai?verb=ListRecords&metadataPrefix=ivo_vor&set=ivo_managed")
    root = etree.fromstring(lr.content, etree.XMLParser(no_network=True, resolve_entities=False))
    idents = [
        el.text.strip()
        for el in root.findall(f".//{{{OAI_NS}}}header/{{{OAI_NS}}}identifier")
        if el.text
    ]
    assert idents[0] == "ivo://ivoa.net/rofr"
    assert idents[1] == "ivo://ivoa.net"
    assert idents[2] == "ivo://ivoa.net/IVOA"
    assert "ivo://ivoa.net/std/ADQL" in idents


@pytest.mark.asyncio
async def test_phase1_oai_explorer_cases(client: AsyncClient) -> None:
    for case in OAI_PHASE1_CASES:
        q = case.query_options.lstrip().lstrip("?")
        r = await client.get(f"/oai?{q}")
        assert r.status_code == 200, case.name
        root = etree.fromstring(r.content, etree.XMLParser(no_network=True, resolve_entities=False))
        codes = extract_error_codes(root)
        ok, msg, _ignored = _error_codes_acceptable(
            codes,
            case.expect_error_one_of,
            case.ignore_errors,
            case.optional_error_one_of,
        )
        assert ok, f"{case.name}: {msg}; codes={codes}; body={r.text[:400]}"


@pytest.mark.asyncio
async def test_phase3_harvest_smoke(client: AsyncClient) -> None:
    r = await client.get("/oai?verb=ListRecords&metadataPrefix=ivo_vor&set=ivo_managed")
    records, _token = extract_records(r.content)
    assert len(records) >= 29
    settings = Settings.from_env()
    validated = False
    for rec in records:
        md = rec.find(f"{{{OAI_NS}}}metadata")
        if md is None or len(md) == 0:
            continue
        errors = xsd_validate.validate_element_tree(md[0], settings.schema_root)
        if not errors:
            validated = True
            break
    assert validated, "expected at least one harvested record to pass XSD validation"


@pytest.mark.asyncio
async def test_identify_validates_oai_envelope(client: AsyncClient) -> None:
    r = await client.get("/oai?verb=Identify")
    assert r.status_code == 200
    assert "ivo://ivoa.net/rofr" in r.text
    settings = Settings.from_env()
    errors = xsd_validate.validate_oai_response_envelope(r.content, settings.schema_root)
    assert not errors, errors[:5]


@pytest.mark.asyncio
async def test_list_records_includes_ivo_managed_setspec(client: AsyncClient) -> None:
    r = await client.get("/oai?verb=ListRecords&metadataPrefix=ivo_vor&set=ivo_managed")
    assert r.status_code == 200
    root = etree.fromstring(r.content, etree.XMLParser(no_network=True, resolve_entities=False))
    first_header = root.find(f".//{{{OAI_NS}}}record/{{{OAI_NS}}}header")
    assert first_header is not None
    set_specs = [
        el.text.strip()
        for el in first_header.findall(f"{{{OAI_NS}}}setSpec")
        if el.text
    ]
    assert "ivo_managed" in set_specs


@pytest.mark.asyncio
async def test_list_sets_includes_ivo_publishers(client: AsyncClient) -> None:
    r = await client.get("/oai?verb=ListSets")
    assert r.status_code == 200
    root = etree.fromstring(r.content, etree.XMLParser(no_network=True, resolve_entities=False))
    specs = {
        el.text.strip()
        for el in root.findall(f".//{{{OAI_NS}}}setSpec")
        if el.text
    }
    assert "ivo_managed" in specs
    assert "ivo_publishers" in specs


@pytest.mark.asyncio
async def test_oai_post_identify(client: AsyncClient) -> None:
    r = await client.post("/oai", data={"verb": "Identify"})
    assert r.status_code == 200
    assert "ivo://ivoa.net/rofr" in r.text


@pytest.mark.asyncio
async def test_oai_resumption_walks_pages(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OAI_MAX_RECORDS", "2")
    transport = client._transport
    assert isinstance(transport, ASGITransport)
    core = fastapi_app(transport.app)
    core.state.settings = Settings.from_env()
    seen: set[str] = set()
    query = "/oai?verb=ListRecords&metadataPrefix=ivo_vor&set=ivo_managed"
    while query:
        r = await client.get(query)
        assert r.status_code == 200
        root = etree.fromstring(r.content, etree.XMLParser(no_network=True, resolve_entities=False))
        for el in root.findall(f".//{{{OAI_NS}}}header/{{{OAI_NS}}}identifier"):
            if el.text:
                seen.add(el.text.strip())
        token_el = root.find(f".//{{{OAI_NS}}}resumptionToken")
        if token_el is None or not (token_el.text and token_el.text.strip()):
            break
        from urllib.parse import quote

        query = f"/oai?verb=ListRecords&resumptionToken={quote(token_el.text.strip(), safe='')}"
    assert len(seen) >= 29
    assert "ivo://ivoa.net/rofr" in seen


@pytest.mark.asyncio
async def test_get_record_includes_setspec(client: AsyncClient) -> None:
    r = await client.get(
        "/oai?verb=GetRecord&metadataPrefix=ivo_vor&identifier=ivo://ivoa.net/rofr"
    )
    assert r.status_code == 200
    root = etree.fromstring(r.content, etree.XMLParser(no_network=True, resolve_entities=False))
    header = root.find(f".//{{{OAI_NS}}}record/{{{OAI_NS}}}header")
    assert header is not None
    specs = [el.text for el in header.findall(f"{{{OAI_NS}}}setSpec") if el.text]
    assert "ivo_managed" in specs
