"""Build OAI ``StandardRecord`` payloads for registered publishing registries."""

from __future__ import annotations

from lxml import etree

from benson.oai.dates import normalize_datestamp
from benson.registry.registry_self import REGISTRY_STD
from benson.registry.standards_store import StandardRecord
from benson.service.rofr_lists import PublisherRegistry

RI_NS = "http://www.ivoa.net/xml/RegistryInterface/v1.0"
VG_NS = "http://www.ivoa.net/xml/VORegistry/v1.0"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"

IVO_PUBLISHERS = "ivo_publishers"
_XML_PARSER = etree.XMLParser(no_network=True, resolve_entities=False)


def publisher_datestamp(rec: PublisherRegistry) -> str:
    raw = rec.updated_at or rec.registered_at
    return normalize_datestamp(raw)


def build_publisher_metadata(rec: PublisherRegistry) -> etree._Element:
    """Minimal harvestable ``vg:Registry`` describing a registered publisher."""
    resource = etree.Element(
        f"{{{RI_NS}}}Resource",
        nsmap={
            "ri": RI_NS,
            "vg": VG_NS,
            "xsi": XSI_NS,
        },
        attrib={
            f"{{{XSI_NS}}}type": "vg:Registry",
            "status": "active",
        },
    )
    title_el = etree.SubElement(resource, f"{{{RI_NS}}}title")
    title_el.text = rec.title
    ident_el = etree.SubElement(resource, f"{{{RI_NS}}}identifier")
    ident_el.text = rec.oai_identifier
    if rec.harvest_access_url:
        cap = etree.SubElement(
            resource,
            f"{{{RI_NS}}}capability",
            attrib={
                "standardID": REGISTRY_STD,
                f"{{{XSI_NS}}}type": "vg:Harvest",
            },
        )
        iface = etree.SubElement(
            cap,
            f"{{{RI_NS}}}interface",
            attrib={
                f"{{{XSI_NS}}}type": "vg:OAIHTTP",
                "role": "std",
                "version": "1.0",
            },
        )
        url_el = etree.SubElement(iface, f"{{{RI_NS}}}accessURL")
        url_el.text = rec.harvest_access_url
    return etree.fromstring(
        etree.tostring(resource, encoding="UTF-8"),
        parser=_XML_PARSER,
    )


def publisher_standard_record(rec: PublisherRegistry) -> StandardRecord:
    return StandardRecord(
        identifier=rec.oai_identifier,
        datestamp=publisher_datestamp(rec),
        resource_status="active",
        metadata=build_publisher_metadata(rec),
        oai_set=IVO_PUBLISHERS,
    )


def publishers_to_standard_records(
    publishers: list[PublisherRegistry],
) -> list[StandardRecord]:
    out = [publisher_standard_record(p) for p in publishers if p.oai_identifier.strip()]
    return sorted(out, key=lambda r: r.identifier)
