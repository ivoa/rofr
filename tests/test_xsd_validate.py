"""XSD validation with bundled IVOA schema catalog."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from lxml import etree

_repo = Path(__file__).resolve().parents[1]
os.environ.setdefault("SCHEMA_ROOT", str(_repo / "assets" / "schemas"))

from benson.oai.phase3 import validate_voresource_documents  # noqa: E402
from benson.config import Settings  # noqa: E402
from benson.xml import xsd_validate  # noqa: E402

_SCHEMA_ROOT = Path(os.environ["SCHEMA_ROOT"])
_VOR_NS = "http://www.ivoa.net/xml/VOResource/v1.0"
_RI_NS = "http://www.ivoa.net/xml/RegistryInterface/v1.0"
_XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"


@pytest.fixture
def cadc_identify_bytes() -> bytes:
    return (_repo / "tests" / "fixtures" / "cadc_identify.xml").read_bytes()


def test_cadc_identify_envelope_passes_builtin_catalog(cadc_identify_bytes: bytes) -> None:
    errors = xsd_validate.validate_oai_response_envelope(cadc_identify_bytes, _SCHEMA_ROOT)
    assert errors == [], errors


def test_cadc_identify_resource_fragment_passes_ivoa_bundle(cadc_identify_bytes: bytes) -> None:
    root = etree.fromstring(cadc_identify_bytes)
    resource = root.find(f".//{{{_RI_NS}}}Resource")
    assert resource is not None
    errors = xsd_validate.validate_element_tree(resource, _SCHEMA_ROOT)
    assert errors == [], errors


def test_parse_schema_location_valid() -> None:
    attr = (
        "http://www.ivoa.net/xml/VOResource/v1.0 http://www.ivoa.net/xml/VOResource/v1.0 "
        "http://www.ivoa.net/xml/RegistryInterface/v1.0 http://www.ivoa.net/xml/RegistryInterface/v1.0"
    )
    pairs = xsd_validate.parse_schema_location(attr)
    assert pairs == [
        ("http://www.ivoa.net/xml/VOResource/v1.0", "http://www.ivoa.net/xml/VOResource/v1.0"),
        (
            "http://www.ivoa.net/xml/RegistryInterface/v1.0",
            "http://www.ivoa.net/xml/RegistryInterface/v1.0",
        ),
    ]


def test_parse_schema_location_malformed() -> None:
    assert xsd_validate.parse_schema_location("one two three") is None


def test_validate_element_tree_declared_passes_minimal_resource() -> None:
    xml = f"""<Resource xmlns="{_RI_NS}" xmlns:vr="{_VOR_NS}" xmlns:xsi="{_XSI_NS}"
  created="2020-01-01T00:00:00Z" updated="2020-01-01T00:00:00Z" status="active"
  xsi:schemaLocation="{_VOR_NS} http://www.ivoa.net/xml/VOResource/v1.0 {_RI_NS} http://www.ivoa.net/xml/RegistryInterface/v1.0">
  <title xmlns="">Test</title>
  <shortName xmlns="">t</shortName>
  <identifier xmlns="">ivo://example/test</identifier>
  <curation xmlns=""><publisher>Example</publisher><contact><name>N</name><email>a@b.c</email></contact></curation>
  <content xmlns=""><subject>Test</subject><description>Desc</description><referenceURL>http://example.org</referenceURL></content>
</Resource>"""
    el = etree.fromstring(xml)
    errors = xsd_validate.validate_element_tree_declared(el, _SCHEMA_ROOT)
    assert errors == [], errors


def test_validate_element_tree_declared_rejects_extension_without_bundle() -> None:
    adql = (_repo / "assets" / "standards" / "adql.xml").read_bytes()
    el = etree.fromstring(adql)
    errors = xsd_validate.validate_element_tree_declared(el, _SCHEMA_ROOT)
    assert errors


def test_validate_element_tree_declared_missing_schema_location() -> None:
    el = etree.fromstring(f'<Resource xmlns="{_VOR_NS}"/>')
    errors = xsd_validate.validate_element_tree_declared(el, _SCHEMA_ROOT)
    assert errors
    assert "Missing xsi:schemaLocation" in errors[0]


def test_validate_element_tree_declared_unresolvable_url() -> None:
    el = etree.fromstring(
        f'<Resource xmlns="{_VOR_NS}" xmlns:xsi="{_XSI_NS}" '
        f'xsi:schemaLocation="{_VOR_NS} http://example.invalid/unknown.xsd"/>'
    )
    errors = xsd_validate.validate_element_tree_declared(el, _SCHEMA_ROOT)
    assert errors
    assert "Cannot resolve declared schema location" in errors[0]


def test_declared_vs_bundled_cadc_resource(cadc_identify_bytes: bytes) -> None:
    root = etree.fromstring(cadc_identify_bytes)
    resource = root.find(f".//{{{_RI_NS}}}Resource")
    assert resource is not None
    assert xsd_validate.validate_element_tree(resource, _SCHEMA_ROOT) == []
    declared = xsd_validate.validate_element_tree_declared(resource, _SCHEMA_ROOT)
    assert declared
    assert "Missing xsi:schemaLocation" in declared[0]


def test_validate_oai_response_declared_cadc(cadc_identify_bytes: bytes) -> None:
    errors = xsd_validate.validate_oai_response_declared(cadc_identify_bytes, _SCHEMA_ROOT)
    assert errors
    assert any("Missing xsi:schemaLocation" in e for e in errors)


_VALID_DECLARED_RESOURCE = f"""<Resource xmlns="{_RI_NS}" xmlns:vr="{_VOR_NS}" xmlns:xsi="{_XSI_NS}"
  created="2020-01-01T00:00:00Z" updated="2020-01-01T00:00:00Z" status="active"
  xsi:schemaLocation="{_VOR_NS} http://www.ivoa.net/xml/VOResource/v1.0 {_RI_NS} http://www.ivoa.net/xml/RegistryInterface/v1.0">
  <title xmlns="">Test</title>
  <shortName xmlns="">t</shortName>
  <identifier xmlns="">ivo://example/test</identifier>
  <curation xmlns=""><publisher>Example</publisher><contact><name>N</name><email>a@b.c</email></contact></curation>
  <content xmlns=""><subject>Test</subject><description>Desc</description><referenceURL>http://example.org</referenceURL></content>
</Resource>""".encode()


def test_validate_voresource_declared_mode_pass_and_fail() -> None:
    settings = Settings.from_env()
    bare = {"ivo://example/bare": f'<Resource xmlns="{_VOR_NS}"/>'.encode()}
    declared = {"ivo://example/ok": _VALID_DECLARED_RESOURCE}

    vor_root_bare, stats_bare = validate_voresource_documents(
        bare, "fail warn rec", builtin_schemas=False, settings=settings
    )
    assert stats_bare.nfail == 1
    bare_tests = vor_root_bare.findall(".//test")
    assert bare_tests
    assert any(t.get("status") == "fail" for t in bare_tests)

    vor_root_ok, stats_ok = validate_voresource_documents(
        declared, "fail warn rec pass", builtin_schemas=False, settings=settings
    )
    assert stats_ok.npass == 1
    assert stats_ok.nfail == 0
    ok_tests = [t for t in vor_root_ok.findall(".//test") if t.get("item")]
    assert len(ok_tests) > 1
    assert not any(t.get("status") == "fail" for t in ok_tests)
