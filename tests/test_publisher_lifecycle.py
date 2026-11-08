"""Withdraw, reactivate, and OAI tombstones for publishing registries."""

from __future__ import annotations

import os
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from lxml import etree

_repo = Path(__file__).resolve().parents[1]
os.environ.setdefault("SCHEMA_ROOT", str(_repo / "assets" / "schemas"))
os.environ.setdefault("ASSETS_ROOT", str(_repo / "assets" / "validate"))

from benson.app import create_app, fastapi_app  # noqa: E402
from benson.config import Settings  # noqa: E402
from benson.registry.publisher_lifecycle import reactivate_publisher, withdraw_publisher
from benson.registry.publishers_store import PublisherStore
from benson.registry.registration import register_publisher
from benson.service.rofr_lists import LISTING_WITHDRAWN, PublisherRegistry, publisher_is_withdrawn
from benson.session.store import HarvestRun, store
from benson.xml import results as R

OAI_NS = "http://www.openarchives.org/OAI/2.0/"


@pytest_asyncio.fixture
async def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncClient:
    pub = tmp_path / "publishers.json"
    monkeypatch.setenv("PUBLISHERS_REGISTRY_FILE", str(pub))
    settings = Settings.from_env()
    app = create_app()
    core = fastapi_app(app)
    async with httpx.AsyncClient() as hc:
        core.state.settings = settings
        core.state.http_client = hc
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest.mark.asyncio
async def test_withdraw_and_reactivate_store(tmp_path: Path) -> None:
    path = tmp_path / "publishers.json"
    ps = PublisherStore(path)
    await ps.upsert(
        PublisherRegistry(
            oai_identifier="ivo://w/reg",
            title="W",
            harvest_access_url="https://w.example/oai",
            registered_at="2026-01-01T00:00:00Z",
        )
    )
    withdrawn = await withdraw_publisher(ps, "ivo://w/reg", reason="test")
    assert publisher_is_withdrawn(withdrawn)
    assert withdrawn.withdrawn_at
    assert withdrawn.withdraw_reason == "test"

    rows = await ps.load()
    assert len(rows) == 1
    assert rows[0].listing_status == LISTING_WITHDRAWN

    active_only = await ps.load_active()
    assert active_only == []

    again = await withdraw_publisher(ps, "ivo://w/reg")
    assert again.oai_identifier == "ivo://w/reg"

    reactivated = await reactivate_publisher(ps, "ivo://w/reg")
    assert not publisher_is_withdrawn(reactivated)
    assert reactivated.withdrawn_at is None
    assert await ps.load_active() == [reactivated]


@pytest.mark.asyncio
async def test_oai_withdrawn_tombstone(client: AsyncClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pub = tmp_path / "publishers.json"
    monkeypatch.setenv("PUBLISHERS_REGISTRY_FILE", str(pub))
    ps = PublisherStore(pub)
    await ps.upsert(
        PublisherRegistry(
            oai_identifier="ivo://tomb/reg",
            title="Tomb",
            harvest_access_url="https://tomb.example/oai",
            registered_at="2026-01-01T00:00:00Z",
        )
    )
    await withdraw_publisher(ps, "ivo://tomb/reg")

    r = await client.get(
        "/oai?verb=ListRecords&metadataPrefix=ivo_vor&set=ivo_publishers"
    )
    assert r.status_code == 200
    root = etree.fromstring(r.content, etree.XMLParser(no_network=True, resolve_entities=False))
    record = root.find(f".//{{{OAI_NS}}}record")
    assert record is not None
    header = record.find(f"{{{OAI_NS}}}header")
    assert header is not None
    assert header.get("status") == "deleted"
    assert record.find(f"{{{OAI_NS}}}metadata") is None

    gr = await client.get(
        "/oai?verb=GetRecord&identifier=ivo://tomb/reg&metadataPrefix=ivo_vor"
    )
    assert gr.status_code == 200
    groot = etree.fromstring(gr.content, etree.XMLParser(no_network=True, resolve_entities=False))
    gheader = groot.find(f".//{{{OAI_NS}}}header")
    assert gheader is not None
    assert gheader.get("status") == "deleted"


@pytest.mark.asyncio
async def test_json_api_hides_withdrawn(client: AsyncClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pub = tmp_path / "publishers.json"
    monkeypatch.setenv("PUBLISHERS_REGISTRY_FILE", str(pub))
    ps = PublisherStore(pub)
    await ps.upsert(
        PublisherRegistry(
            oai_identifier="ivo://vis/reg",
            title="Visible",
            harvest_access_url="https://vis.example/oai",
            registered_at="2026-01-01T00:00:00Z",
        )
    )
    await ps.upsert(
        PublisherRegistry(
            oai_identifier="ivo://hid/reg",
            title="Hidden",
            harvest_access_url="https://hid.example/oai",
            registered_at="2026-01-01T00:00:00Z",
            listing_status=LISTING_WITHDRAWN,
            withdrawn_at="2026-06-01T00:00:00Z",
        )
    )
    r = await client.get("/api/v1/registry/publishers")
    assert r.status_code == 200
    data = r.json()
    ids = {row["oai_identifier"] for row in data}
    assert ids == {"ivo://vis/reg"}


@pytest.mark.asyncio
async def test_register_reactivates_withdrawn(
    client: AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pub = tmp_path / "publishers.json"
    monkeypatch.setenv("PUBLISHERS_REGISTRY_FILE", str(pub))
    settings = Settings.from_env()
    ps = PublisherStore(pub)
    await ps.upsert(
        PublisherRegistry(
            oai_identifier="ivo://back/reg",
            title="Old",
            harvest_access_url="https://old.example/oai",
            registered_at="2025-01-01T00:00:00Z",
            listing_status=LISTING_WITHDRAWN,
            withdrawn_at="2026-01-01T00:00:00Z",
        )
    )

    run = HarvestRun(
        run_id="reactivate-reg",
        endpoint="https://new-endpoint.example/oai?",
        builtin_schemas=True,
        cache=True,
        show_status="fail warn rec",
        fmt="html",
        error_fmt="html",
        identify_oai_identifier="ivo://back/reg",
        identify_title="Back Again",
    )
    root = R.registry_validation_root(status="completed", nfail="0", nwarn="0", nrec="0")
    run.merged_validation = etree.ElementTree(root)
    await store.create(run)

    result = await register_publisher(
        "reactivate-reg",
        oai_identifier="ivo://back/reg",
        title="Back Again",
        settings=settings,
    )
    assert result.created is False
    assert not publisher_is_withdrawn(result.record)
    assert "new-endpoint.example" in (result.record.harvest_access_url or "")

    rows = await ps.load()
    assert len(rows) == 1
    assert not publisher_is_withdrawn(rows[0])
