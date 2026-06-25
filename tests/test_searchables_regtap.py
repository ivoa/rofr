"""Tests for RegTAP-backed full searchable registries."""

from __future__ import annotations

import os
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

_repo = Path(__file__).resolve().parents[1]
os.environ.setdefault("SCHEMA_ROOT", str(_repo / "docs" / "schemas"))
os.environ.setdefault("ASSETS_ROOT", str(_repo / "assets" / "validate"))

from benson.config import Settings  # noqa: E402
from benson.service.searchables_regtap import (  # noqa: E402
    DEFAULT_SEARCHABLES_ADQL,
    fetch_searchables_from_regtap,
    load_searchables,
    parse_searchables_regtap_csv,
)


def _clear_searchables_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for k in (
        "SEARCHABLES_CACHE_FILE",
        "SEARCHABLES_CACHE_DIR",
        "SEARCHABLES_CACHE_MAX_AGE_SEC",
        "SEARCHABLES_ADQL",
        "SEARCHABLES_REGTAP_SYNC_URL",
    ):
        monkeypatch.delenv(k, raising=False)


_CSV_HEADER = "ivoid,res_type,res_title,reference_url,civoid,cap_type,standard_id,intf_type,url_use,access_url"
_CSV_ROW_PARAM = (
    "ivo://example/reg,vg:registry,Example VO,https://registry.example/,"
    "ivo://example/reg,cap,sid,vs:paramhttp,full,https://registry.example/tap"
)
_CSV_ROW_SEARCH = (
    "ivo://example/s,vg:registry,Search VO,https://search.example/,"
    "ivo://example/s,cap,sid,vs:webservice,full,https://search.example/svc"
)


def test_default_adql_matches_select_shape() -> None:
    assert "rr.capability" in DEFAULT_SEARCHABLES_ADQL
    assert "rr.resource" in DEFAULT_SEARCHABLES_ADQL
    assert "vg:registry" in DEFAULT_SEARCHABLES_ADQL


def test_parse_searchables_regtap_csv_paramhttp_label() -> None:
    text = f"{_CSV_HEADER}\n{_CSV_ROW_PARAM}\n"
    rows = parse_searchables_regtap_csv(text)
    assert len(rows) == 1
    r = rows[0]
    assert r.title == "Example VO"
    assert r.href == "https://registry.example/"
    assert r.fields["IVOA Identifier"] == "ivo://example/reg"
    assert r.fields["RegTAP service endpoint"] == "https://registry.example/tap"


def test_parse_searchables_regtap_csv_search_label() -> None:
    text = f"{_CSV_HEADER}\n{_CSV_ROW_SEARCH}\n"
    rows = parse_searchables_regtap_csv(text)
    assert rows[0].fields["Search service endpoint"] == "https://search.example/svc"


def test_parse_skips_wrong_column_count() -> None:
    text = f"{_CSV_HEADER}\n1,2,3\n{_CSV_ROW_PARAM}\n"
    rows = parse_searchables_regtap_csv(text)
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_load_searchables_cache_dir_latest_csv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _clear_searchables_env(monkeypatch)
    d = tmp_path / "csvdir"
    d.mkdir()
    a = d / "a.csv"
    b = d / "b.csv"
    a.write_text(f"{_CSV_HEADER}\n{_CSV_ROW_PARAM}\n", encoding="utf-8")
    b.write_text(f"{_CSV_HEADER}\n{_CSV_ROW_SEARCH}\n", encoding="utf-8")
    old = time.time() - 120.0
    os.utime(a, (old, old))
    monkeypatch.setenv("SEARCHABLES_CACHE_DIR", str(d))
    monkeypatch.setenv("SEARCHABLES_CACHE_MAX_AGE_SEC", "3600")
    settings = Settings.from_env()
    async with httpx.AsyncClient() as client:
        rows = await load_searchables(client, settings, timeout_sec=30.0)
    assert len(rows) == 1
    assert rows[0].title == "Search VO"


@pytest.mark.asyncio
async def test_load_searchables_prefers_fresh_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _clear_searchables_env(monkeypatch)
    csv_path = tmp_path / "searchables.csv"
    csv_path.write_text(f"{_CSV_HEADER}\n{_CSV_ROW_PARAM}\n", encoding="utf-8")
    monkeypatch.setenv("SEARCHABLES_CACHE_FILE", str(csv_path))
    monkeypatch.setenv("SEARCHABLES_CACHE_MAX_AGE_SEC", "3600")
    settings = Settings.from_env()
    async with httpx.AsyncClient() as client:
        rows = await load_searchables(client, settings, timeout_sec=30.0)
    assert len(rows) == 1
    assert rows[0].title == "Example VO"


@pytest.mark.asyncio
async def test_stale_cache_calls_regtap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _clear_searchables_env(monkeypatch)
    csv_path = tmp_path / "searchables.csv"
    csv_path.write_text(f"{_CSV_HEADER}\n{_CSV_ROW_PARAM}\n", encoding="utf-8")
    old = time.time() - 60.0
    os.utime(csv_path, (old, old))
    monkeypatch.setenv("SEARCHABLES_CACHE_FILE", str(csv_path))
    monkeypatch.setenv("SEARCHABLES_CACHE_MAX_AGE_SEC", "30")
    monkeypatch.setenv("SEARCHABLES_REGTAP_SYNC_URL", "https://example.invalid/tap")
    settings = Settings.from_env()
    client = AsyncMock(spec=httpx.AsyncClient)
    resp = MagicMock()
    resp.text = f"{_CSV_HEADER}\n{_CSV_ROW_SEARCH}\n"
    resp.raise_for_status = MagicMock()
    client.post = AsyncMock(return_value=resp)

    rows = await load_searchables(client, settings, timeout_sec=5.0)
    client.post.assert_awaited_once()
    assert len(rows) == 1
    assert rows[0].title == "Search VO"
    assert csv_path.read_text(encoding="utf-8") == f"{_CSV_HEADER}\n{_CSV_ROW_SEARCH}\n"


@pytest.mark.asyncio
async def test_regtap_fetch_writes_cache_to_empty_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _clear_searchables_env(monkeypatch)
    cache_dir = tmp_path / "searchables"
    monkeypatch.setenv("SEARCHABLES_CACHE_DIR", str(cache_dir))
    monkeypatch.setenv("SEARCHABLES_REGTAP_SYNC_URL", "https://tap.test/sync")
    settings = Settings.from_env()
    client = AsyncMock(spec=httpx.AsyncClient)
    resp = MagicMock()
    resp.text = f"{_CSV_HEADER}\n{_CSV_ROW_PARAM}\n"
    resp.raise_for_status = MagicMock()
    client.post = AsyncMock(return_value=resp)

    rows = await load_searchables(client, settings, timeout_sec=5.0)
    assert len(rows) == 1
    cache_file = cache_dir / "registries.csv"
    assert cache_file.is_file()
    assert cache_file.read_text(encoding="utf-8") == resp.text


@pytest.mark.asyncio
async def test_second_load_uses_written_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _clear_searchables_env(monkeypatch)
    cache_dir = tmp_path / "searchables"
    monkeypatch.setenv("SEARCHABLES_CACHE_DIR", str(cache_dir))
    monkeypatch.setenv("SEARCHABLES_CACHE_MAX_AGE_SEC", "3600")
    monkeypatch.setenv("SEARCHABLES_REGTAP_SYNC_URL", "https://tap.test/sync")
    settings = Settings.from_env()
    client = AsyncMock(spec=httpx.AsyncClient)
    resp = MagicMock()
    resp.text = f"{_CSV_HEADER}\n{_CSV_ROW_PARAM}\n"
    resp.raise_for_status = MagicMock()
    client.post = AsyncMock(return_value=resp)

    rows1 = await load_searchables(client, settings, timeout_sec=5.0)
    rows2 = await load_searchables(client, settings, timeout_sec=5.0)
    assert len(rows1) == 1
    assert rows2 == rows1
    client.post.assert_awaited_once()


@pytest.mark.asyncio
async def test_fetch_searchables_from_regtap_posts_form(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_searchables_env(monkeypatch)
    monkeypatch.setenv("SEARCHABLES_REGTAP_SYNC_URL", "https://tap.test/sync")
    settings = Settings.from_env()
    client = AsyncMock(spec=httpx.AsyncClient)
    resp = MagicMock()
    resp.text = f"{_CSV_HEADER}\n{_CSV_ROW_PARAM}\n"
    resp.raise_for_status = MagicMock()
    client.post = AsyncMock(return_value=resp)

    rows = await fetch_searchables_from_regtap(client, settings, timeout_sec=5.0)
    assert rows[0].title == "Example VO"
    aw = client.post.await_args
    assert aw is not None
    assert aw.kwargs["data"]["LANG"] == "ADQL"
    assert aw.kwargs["data"]["responseformat"] == "csv"
    assert "select" in aw.kwargs["data"]["QUERY"].lower()


@pytest.mark.asyncio
async def test_custom_adql_override(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_searchables_env(monkeypatch)
    monkeypatch.setenv("SEARCHABLES_REGTAP_SYNC_URL", "https://tap.test/sync")
    monkeypatch.setenv("SEARCHABLES_ADQL", "select top 1 * from foo")
    settings = Settings.from_env()
    client = AsyncMock(spec=httpx.AsyncClient)
    resp = MagicMock()
    resp.text = f"{_CSV_HEADER}\n{_CSV_ROW_PARAM}\n"
    resp.raise_for_status = MagicMock()
    client.post = AsyncMock(return_value=resp)
    await fetch_searchables_from_regtap(client, settings, timeout_sec=5.0)
    assert client.post.await_args.kwargs["data"]["QUERY"] == "select top 1 * from foo"
