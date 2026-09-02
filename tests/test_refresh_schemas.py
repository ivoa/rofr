"""Refresh bundled IVOA XSDs from namespace URLs."""

from __future__ import annotations

import httpx

from benson.xml.catalog import NAMESPACE_SCHEMA_FILES
from benson.xml.refresh_schemas import ivoa_catalog_entries, refresh


def test_ivoa_catalog_entries_are_ivoa_net_only() -> None:
    entries = ivoa_catalog_entries()
    assert entries
    assert all(url.startswith("http://www.ivoa.net/xml/") for url, _ in entries)
    assert all(fname.endswith(".xsd") for _, fname in entries)
    assert len(entries) < len(NAMESPACE_SCHEMA_FILES)


def test_refresh_overwrites_on_success_keeps_file_on_failure(tmp_path, monkeypatch) -> None:
    from benson.xml import refresh_schemas as mod

    dest = tmp_path / "VOResource-v1.xsd"
    dest.write_text("old")
    other = tmp_path / "missing.xsd"
    other.write_text("keep")

    bodies = {
        "http://www.ivoa.net/xml/VOResource/v1.0": b"<xs:schema version='1.2'/>",
    }

    def fake_get(url, **_kwargs):
        request = httpx.Request("GET", url)
        if url not in bodies:
            return httpx.Response(404, request=request, text="Not Found")
        return httpx.Response(200, request=request, content=bodies[url])

    monkeypatch.setattr(
        mod,
        "ivoa_catalog_entries",
        lambda: [
            ("http://www.ivoa.net/xml/VOResource/v1.0", "VOResource-v1.xsd"),
            ("http://www.ivoa.net/xml/missing/v1.0", "missing.xsd"),
        ],
    )
    monkeypatch.setattr(mod.httpx, "get", fake_get)

    written, errors = refresh(tmp_path)
    assert written == [dest]
    assert dest.read_bytes() == b"<xs:schema version='1.2'/>"
    assert other.read_text() == "keep"
    assert any("missing" in e for e in errors)


def test_download_retries_transient_errors(monkeypatch) -> None:
    from benson.xml import refresh_schemas as mod

    calls = {"n": 0}

    def flaky_get(url, **_kwargs):
        calls["n"] += 1
        request = httpx.Request("GET", url)
        if calls["n"] < 3:
            raise httpx.ReadError("IncompleteRead", request=request)
        return httpx.Response(200, request=request, content=b"<xs:schema/>")

    monkeypatch.setattr(mod.httpx, "get", flaky_get)
    assert mod._download("http://www.ivoa.net/xml/VOResource/v1.0") == b"<xs:schema/>"
    assert calls["n"] == 3


def test_refresh_normalizes_crlf_to_lf(tmp_path, monkeypatch) -> None:
    from benson.xml import refresh_schemas as mod

    dest = tmp_path / "VOResource-v1.xsd"

    def fake_get(url, **_kwargs):
        request = httpx.Request("GET", url)
        return httpx.Response(
            200,
            request=request,
            content=b"<?xml version='1.0'?>\r\n<xs:schema/>\r\n",
        )

    monkeypatch.setattr(
        mod,
        "ivoa_catalog_entries",
        lambda: [("http://www.ivoa.net/xml/VOResource/v1.0", "VOResource-v1.xsd")],
    )
    monkeypatch.setattr(mod.httpx, "get", fake_get)

    written, errors = refresh(tmp_path)
    assert errors == []
    assert written == [dest]
    assert dest.read_bytes() == b"<?xml version='1.0'?>\n<xs:schema/>\n"
