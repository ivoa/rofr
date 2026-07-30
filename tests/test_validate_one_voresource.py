"""Single-record VOResource validation (``validate_one_voresource``)."""

from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest
from lxml import etree

_repo = Path(__file__).resolve().parents[1]
os.environ.setdefault("SCHEMA_ROOT", str(_repo / "assets" / "schemas"))
os.environ.setdefault("ASSETS_ROOT", str(_repo / "assets" / "validate"))

from benson.config import Settings  # noqa: E402
from benson.oai.phase3 import validate_one_voresource, validate_voresource_documents  # noqa: E402
from benson.xml.xslt_eval import XsltAssetsError  # noqa: E402

_RI = "http://www.ivoa.net/xml/RegistryInterface/v1.0"
_VR = "http://www.ivoa.net/xml/VOResource/v1.0"

# Minimal well-formed RI resource (not necessarily XSD-valid).
_MINIMAL_VOR = f"""\
<?xml version="1.0"?>
<ri:Resource xmlns:ri="{_RI}" xmlns:vr="{_VR}"
    created="2020-01-01T00:00:00Z" updated="2020-01-01T00:00:00Z"
    status="active">
  <title>Example</title>
  <identifier>ivo://example/test</identifier>
  <curation>
    <publisher>Example</publisher>
  </curation>
  <content>
    <subject>testing</subject>
    <description>minimal fixture</description>
    <referenceURL>http://example.com/</referenceURL>
  </content>
</ri:Resource>
""".encode()


@pytest.fixture
def settings() -> Settings:
    return Settings.from_env()


def _fake_xslt_tree(*tests: etree._Element) -> etree._ElementTree:
    root = etree.Element("VOResourceValidation")
    for t in tests:
        root.append(t)
    return etree.ElementTree(root)


def test_validate_one_raises_on_malformed_xml(settings: Settings) -> None:
    with pytest.raises(etree.XMLSyntaxError):
        validate_one_voresource(b"<not-closed>", builtin_schemas=False, settings=settings)


def test_validate_one_surfaces_xsd_errors(settings: Settings) -> None:
    errs = validate_one_voresource(
        _MINIMAL_VOR,
        builtin_schemas=True,
        settings=settings,
    )
    assert errs, "expected schema violations for incomplete resource"


def test_validate_one_skips_xsd_when_builtin_disabled(settings: Settings) -> None:
    with patch(
        "benson.oai.phase3.xslt_eval.transform",
        return_value=_fake_xslt_tree(),
    ):
        errs = validate_one_voresource(
            _MINIMAL_VOR,
            builtin_schemas=False,
            settings=settings,
        )
    assert errs == []


def test_validate_one_missing_stylesheet_fails_hard(
    settings: Settings,
    tmp_path: Path,
) -> None:
    """Missing XSLT assets must fail hard, not silently skip rule checks."""
    broken = replace(settings, assets_root=tmp_path)
    with pytest.raises(XsltAssetsError, match="Required XSLT stylesheet missing"):
        validate_one_voresource(_MINIMAL_VOR, builtin_schemas=False, settings=broken)


def test_validate_one_stylesheet_load_failure_fails_hard(
    settings: Settings,
    tmp_path: Path,
) -> None:
    """Unloadable stylesheets (e.g. broken imports) must fail hard with fix guidance."""
    (tmp_path / "checkVOResource.xsl").write_text(
        '<?xml version="1.0"?>\n'
        '<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">\n'
        '  <xsl:import href="does-not-exist.xsl"/>\n'
        "</xsl:stylesheet>\n",
        encoding="utf-8",
    )
    broken = replace(settings, assets_root=tmp_path)
    with pytest.raises(XsltAssetsError, match="Failed to load XSLT stylesheet"):
        validate_one_voresource(_MINIMAL_VOR, builtin_schemas=False, settings=broken)


def test_validate_one_collects_xslt_fail_tests(settings: Settings) -> None:
    fail = etree.Element("test", item="use-voc-content_type", status="fail")
    fail.text = "#bogus not in vocabulary"
    warn = etree.Element("test", item="use-voc-uat", status="warn")
    warn.text = "#old deprecated"
    ok = etree.Element("test", item="VRvalid", status="pass")
    ok.text = "OK"
    xout = _fake_xslt_tree(fail, warn, ok)

    with patch("benson.oai.phase3.xslt_eval.transform", return_value=xout):
        errs = validate_one_voresource(
            _MINIMAL_VOR,
            builtin_schemas=False,
            settings=settings,
        )

    assert errs == ["use-voc-content_type: #bogus not in vocabulary"]


def test_validate_one_xslt_pass_yields_no_errors(settings: Settings) -> None:
    ok = etree.Element("test", item="VRvalid", status="pass")
    ok.text = "OK"
    with patch("benson.oai.phase3.xslt_eval.transform", return_value=_fake_xslt_tree(ok)):
        errs = validate_one_voresource(
            _MINIMAL_VOR,
            builtin_schemas=False,
            settings=settings,
        )
    assert errs == []


def test_validate_one_passes_current_rightnow(settings: Settings) -> None:
    """Past created/updated dates must not fail VRdate when rightnow is current."""
    from benson.xml import xslt_eval

    # Ensure the stylesheet actually loads (no silent XSLT fallback).
    xslt_eval.transform(
        settings.assets_root / "checkVOResource.xsl",
        etree.fromstring(_MINIMAL_VOR),
        params={"rightnow": xslt_eval.rightnow()},
    )

    errs = validate_one_voresource(
        _MINIMAL_VOR,
        builtin_schemas=False,
        settings=settings,
    )
    assert not any(e.startswith("VRdate:") for e in errs)


def test_validate_one_stale_rightnow_fails_vrdate(settings: Settings) -> None:
    """A stale evaluation clock must still surface VRdate failures."""
    from benson.xml import xslt_eval

    out = xslt_eval.transform(
        settings.assets_root / "checkVOResource.xsl",
        etree.fromstring(_MINIMAL_VOR),
        params={"rightnow": "2007-02-24T14:49:50"},
    )
    fails = [
        t
        for t in out.getroot().findall("test")
        if t.get("item") == "VRdate" and t.get("status") == "fail"
    ]
    assert fails
    assert any("created attribute" in (t.text or "") for t in fails)


def test_validate_one_passes_rightnow_param_to_xslt(settings: Settings) -> None:
    captured: dict[str, str] = {}

    def _capture(xsl_path, el, *, params=None):  # noqa: ANN001
        captured.update(params or {})
        return _fake_xslt_tree()

    with patch("benson.oai.phase3.xslt_eval.transform", side_effect=_capture):
        with patch(
            "benson.oai.phase3.xslt_eval.rightnow",
            return_value="2026-07-29T12:00:00",
        ):
            validate_one_voresource(
                _MINIMAL_VOR,
                builtin_schemas=False,
                settings=settings,
            )

    assert captured.get("rightnow") == "2026-07-29T12:00:00"


def test_validate_one_voc_exercise_xsd_reports_errors(settings: Settings) -> None:
    blob = (_repo / "tests" / "fixtures" / "voc-exercise.vor").read_bytes()
    with patch(
        "benson.oai.phase3.xslt_eval.transform",
        return_value=_fake_xslt_tree(),
    ):
        errs = validate_one_voresource(blob, builtin_schemas=True, settings=settings)
    assert any("stats" in e for e in errs)


def test_validate_voresource_documents_uses_validate_one(settings: Settings) -> None:
    fail = etree.Element("test", item="use-voc-messenger", status="fail")
    fail.text = "#nope not in vocabulary"
    with patch(
        "benson.oai.phase3.xslt_eval.transform",
        return_value=_fake_xslt_tree(fail),
    ):
        root, stats = validate_voresource_documents(
            {"ivo://example/test": _MINIMAL_VOR},
            "fail warn rec",
            builtin_schemas=False,
            settings=settings,
        )
    assert stats.nfail == 1
    assert stats.npass == 0
    test = root.find(".//test")
    assert test is not None
    assert test.get("status") == "fail"
    assert "use-voc-messenger" in (test.text or "")
