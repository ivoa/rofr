"""OAI tombstones for withdrawn IVOA standards (PR-D)."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from lxml import etree

from benson.app import create_app, fastapi_app
from benson.config import Settings
from benson.registry.standards_store import StandardsStore

_repo = Path(__file__).resolve().parents[1]
_AUTHORITY_SRC = _repo / "assets" / "authority" / "ivoa.xml"

OAI_NS = "http://www.openarchives.org/OAI/2.0/"
RI_NS = "http://www.ivoa.net/xml/RegistryInterface/v1.0"


@pytest_asyncio.fixture
async def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncClient:
    standards = tmp_path / "standards"
    standards.mkdir()
    auth_dir = tmp_path / "authority"
    auth_dir.mkdir()
    if _AUTHORITY_SRC.is_file():
        (auth_dir / "ivoa.xml").write_text(
            _AUTHORITY_SRC.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    (standards / "active.xml").write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<ri:Resource xmlns:ri="{RI_NS}"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:type="vstd:Standard"
  xmlns:vstd="http://www.ivoa.net/xml/StandardsRegExt/v1.0"
  status="active" updated="2020-01-01T00:00:00Z">
  <identifier>ivo://ivoa.net/std/ActiveStd</identifier>
  <title>Active Standard</title>
</ri:Resource>
""",
        encoding="utf-8",
    )
    (standards / "deleted-inline.xml").write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<ri:Resource xmlns:ri="{RI_NS}"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:type="vstd:Standard"
  xmlns:vstd="http://www.ivoa.net/xml/StandardsRegExt/v1.0"
  status="deleted" updated="2026-06-01T12:00:00Z">
  <identifier>ivo://ivoa.net/std/DeletedInline</identifier>
  <title>Deleted inline</title>
</ri:Resource>
""",
        encoding="utf-8",
    )
    (standards / "withdrawn_standards.json").write_text(
        """[
  {
    "identifier": "ivo://ivoa.net/std/RemovedFile",
    "withdrawn_at": "2026-07-01T00:00:00Z",
    "withdraw_reason": "standard retired"
  }
]
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("STANDARDS_DIR", str(standards))
    settings = Settings.from_env()
    app = create_app()
    core = fastapi_app(app)
    async with httpx.AsyncClient() as hc:
        core.state.settings = settings
        core.state.http_client = hc
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


def test_standards_store_manifest_tombstone(tmp_path: Path) -> None:
    standards = tmp_path / "std"
    standards.mkdir()
    (standards / "withdrawn_standards.json").write_text(
        '[{"identifier": "ivo://ivoa.net/std/Gone", "withdrawn_at": "2026-01-02T00:00:00Z"}]',
        encoding="utf-8",
    )
    store = StandardsStore(standards)
    records = {r.identifier: r for r in store.standards()}
    assert "ivo://ivoa.net/std/Gone" in records
    assert records["ivo://ivoa.net/std/Gone"].resource_status == "deleted"


@pytest.mark.asyncio
async def test_oai_tombstones_list_and_get(client: AsyncClient) -> None:
    for ident in ("ivo://ivoa.net/std/DeletedInline", "ivo://ivoa.net/std/RemovedFile"):
        lr = await client.get(
            "/oai?verb=ListRecords&metadataPrefix=ivo_vor&set=ivo_managed"
        )
        assert lr.status_code == 200
        root = etree.fromstring(lr.content)
        record = None
        for rec in root.findall(f".//{{{OAI_NS}}}record"):
            hid = rec.find(f"{{{OAI_NS}}}header/{{{OAI_NS}}}identifier")
            if hid is not None and hid.text and hid.text.strip() == ident:
                record = rec
                break
        assert record is not None, ident
        header = record.find(f"{{{OAI_NS}}}header")
        assert header is not None
        assert header.get("status") == "deleted"
        assert record.find(f"{{{OAI_NS}}}metadata") is None

        from urllib.parse import quote

        gr = await client.get(
            f"/oai?verb=GetRecord&identifier={quote(ident, safe='')}&metadataPrefix=ivo_vor"
        )
        assert gr.status_code == 200
        groot = etree.fromstring(gr.content)
        gheader = groot.find(f".//{{{OAI_NS}}}header")
        assert gheader is not None
        assert gheader.get("status") == "deleted"
        assert groot.find(f".//{{{OAI_NS}}}metadata") is None


@pytest.mark.asyncio
async def test_oai_active_standard_still_has_metadata(client: AsyncClient) -> None:
    from urllib.parse import quote

    ident = quote("ivo://ivoa.net/std/ActiveStd", safe="")
    gr = await client.get(
        f"/oai?verb=GetRecord&identifier={ident}&metadataPrefix=ivo_vor"
    )
    assert gr.status_code == 200
    root = etree.fromstring(gr.content)
    assert root.find(f".//{{{OAI_NS}}}metadata") is not None
