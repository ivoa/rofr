"""Single-record VOResource validation (``validate_one_voresource``)."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from lxml import etree

_repo = Path(__file__).resolve().parents[1]
os.environ.setdefault("SCHEMA_ROOT", str(_repo / "assets" / "schemas"))
os.environ.setdefault("ASSETS_ROOT", str(_repo / "assets" / "validate"))

from benson.config import Settings  # noqa: E402
from benson.oai.phase3 import validate_one_voresource, validate_voresource_documents  # noqa: E402

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
    with patch("benson.oai.phase3.xslt_eval.transform", side_effect=etree.XSLTParseError("boom")):
        errs = validate_one_voresource(
            _MINIMAL_VOR,
            builtin_schemas=False,
            settings=settings,
        )
    assert errs == []


def test_validate_one_xslt_failure_falls_back(settings: Settings) -> None:
    """XSLT load/apply errors must not crash; fall back to XSD-only results."""
    with patch(
        "benson.oai.phase3.xslt_eval.transform",
        side_effect=etree.XSLTParseError("Cannot resolve URI testsVOResource-v1_0.xsl"),
    ):
        errs = validate_one_voresource(
            _MINIMAL_VOR,
            builtin_schemas=False,
            settings=settings,
        )
    assert errs == []


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


def test_validate_one_voc_exercise_xsd_reports_errors(settings: Settings) -> None:
    blob = (_repo / "tests" / "fixtures" / "voc-exercise.vor").read_bytes()
    with patch(
        "benson.oai.phase3.xslt_eval.transform",
        side_effect=etree.XSLTParseError("unavailable"),
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
