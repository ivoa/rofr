"""Phase 2 IVOA XSLT parameter wiring."""

from __future__ import annotations

from pathlib import Path

from lxml import etree

from benson.config import Settings
from benson.http.validation_report import render_validation_report
from benson.xml import xslt_eval

_repo = Path(__file__).resolve().parents[1]
_CADC_IDENTIFY = (_repo / "tests" / "fixtures" / "cadc_identify.xml").read_bytes()
_ENDPOINT = "https://ws.cadc-ccda.hia-iha.nrc-cnrc.gc.ca/reg/oai?"


def _ivoa_xslt_params(*, show_status: str) -> dict[str, str]:
    return {
        "expectError": "false",
        "showStatus": show_status,
        "baseurl": _ENDPOINT.rstrip(),
    }


def _identify_tests(show_status: str) -> list[etree._Element]:
    settings = Settings.from_env()
    parsed = etree.fromstring(_CADC_IDENTIFY)
    xsl = settings.assets_root / "checkIVOAOAI.xsl"
    xout = xslt_eval.transform(xsl, parsed, params=_ivoa_xslt_params(show_status=show_status))
    return [
        el
        for el in xout.getroot().iter()
        if etree.QName(el).localname == "test"
        and (el.get("item") or "").startswith("RI3.1.5")
    ]


def test_ivoa_xslt_hides_passing_checks_when_show_omits_pass() -> None:
    tests = _identify_tests("fail warn rec")
    assert tests == []


def test_ivoa_xslt_marks_failures_and_warnings_with_expected_status() -> None:
    xml = b"""<?xml version="1.0"?>
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <responseDate>2026-01-01T00:00:00Z</responseDate>
  <request verb="Identify">https://example/oai</request>
  <Identify>
    <repositoryName>Test</repositoryName>
    <baseURL>https://example/oai</baseURL>
    <protocolVersion>2.0</protocolVersion>
    <adminEmail>a@b.c</adminEmail>
    <description>
      <Resource xmlns="http://www.ivoa.net/xml/RegistryInterface/v1.0"
                xmlns:vg="http://www.ivoa.net/xml/VORegistry/v1.0"
                xmlns:vr="http://www.ivoa.net/xml/VOResource/v1.0"
                xsi:type="vg:Registry" status="active"
                created="2020-01-01T00:00:00Z" updated="2020-01-01T00:00:00Z">
        <title xmlns="">T</title>
        <shortName xmlns="">t</shortName>
        <identifier xmlns="">ivo://example/reg</identifier>
        <curation xmlns=""><publisher>P</publisher><contact><name>N</name><email>a@b.c</email></contact></curation>
        <content xmlns=""><subject>s</subject><description>d</description><referenceURL>http://x</referenceURL></content>
      </Resource>
    </description>
  </Identify>
</OAI-PMH>"""
    settings = Settings.from_env()
    xsl = settings.assets_root / "checkIVOAOAI.xsl"
    xout = xslt_eval.transform(
        xsl,
        etree.fromstring(xml),
        params=_ivoa_xslt_params(show_status="fail warn rec"),
    )
    by_item = {
        el.get("item"): el.get("status")
        for el in xout.getroot().iter()
        if etree.QName(el).localname == "test"
    }
    assert by_item["RI3.1.5b4"] == "warn"
    assert "RI3.1.5b1" not in by_item


def test_render_identify_does_not_style_passing_profile_checks_as_pass() -> None:
    tests = _identify_tests("fail warn rec")
    tq = etree.Element(
        "testQuery",
        name="Identify",
        options="verb=Identify",
        role="Identify",
    )
    for test in tests:
        tq.append(test)
    root = etree.Element("HarvestValidation", baseURL=_ENDPOINT, showStatus="fail warn rec")
    root.append(tq)
    html = render_validation_report(etree.ElementTree(root))
    assert "val-test--pass" not in html
    assert "RI3.1.5b1" not in html


def test_render_identify_shows_warning_styling_for_profile_warnings() -> None:
    xml = b"""<?xml version="1.0"?>
<HarvestValidation baseURL="https://example/oai?" showStatus="fail warn rec">
  <testQuery name="Identify" options="verb=Identify" role="Identify">
    <test item="RI3.1.5b4" status="warn">A Harvesting Registry should declare a Harvest capability.</test>
  </testQuery>
</HarvestValidation>"""
    html = render_validation_report(etree.ElementTree(etree.fromstring(xml)))
    assert "val-test--warn" in html
    assert "val-test--pass" not in html
    assert "Harvest capability" in html
