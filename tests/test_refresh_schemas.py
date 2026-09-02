"""Refresh bundled IVOA XSDs from namespace URLs."""

from __future__ import annotations

from urllib.error import HTTPError

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

    def fake_urlopen(url, timeout=None):
        if url not in bodies:
            raise HTTPError(url, 404, "Not Found", hdrs=None, fp=None)

        class _Resp:
            def read(self) -> bytes:
                return bodies[url]

            def __enter__(self):
                return self

            def __exit__(self, *args) -> None:
                return None

        return _Resp()

    monkeypatch.setattr(
        mod,
        "ivoa_catalog_entries",
        lambda: [
            ("http://www.ivoa.net/xml/VOResource/v1.0", "VOResource-v1.xsd"),
            ("http://www.ivoa.net/xml/missing/v1.0", "missing.xsd"),
        ],
    )
    monkeypatch.setattr(mod, "urlopen", fake_urlopen)

    written, errors = refresh(tmp_path)
    assert written == [dest]
    assert dest.read_bytes() == b"<xs:schema version='1.2'/>"
    assert other.read_text() == "keep"
    assert any("missing" in e for e in errors)
