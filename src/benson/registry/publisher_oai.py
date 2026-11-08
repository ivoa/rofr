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


def _parsed_identify_resource(rec: PublisherRegistry) -> etree._Element | None:
    raw = (rec.identify_resource_xml or "").strip()
    if not raw:
        return None
    try:
        return etree.fromstring(
            raw.encode("utf-8"),
            parser=_XML_PARSER,
        )
    except etree.XMLSyntaxError:
        return None


def publisher_datestamp(rec: PublisherRegistry) -> str:
    resource = _parsed_identify_resource(rec)
    if resource is not None:
        updated = resource.get("updated")
        if updated and str(updated).strip():
            return normalize_datestamp(str(updated).strip())
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


def publisher_metadata_element(rec: PublisherRegistry) -> etree._Element:
    """OAI ``ivo_publishers`` metadata: stored Identify ``vg:Registry`` or a minimal stub."""
    resource = _parsed_identify_resource(rec)
    if resource is not None:
        return etree.fromstring(
            etree.tostring(resource, encoding="UTF-8"),
            parser=_XML_PARSER,
        )
    return build_publisher_metadata(rec)


def _resource_identifier(metadata: etree._Element) -> str | None:
    for el in metadata.iter():
        if not isinstance(el.tag, str):
            continue
        if el.tag.rsplit("}", 1)[-1] == "identifier" and el.text and el.text.strip():
            return el.text.strip()
    return None


def publisher_standard_record(rec: PublisherRegistry) -> StandardRecord:
    metadata = publisher_metadata_element(rec)
    ident = _resource_identifier(metadata) or rec.oai_identifier.strip()
    return StandardRecord(
        identifier=ident,
        datestamp=publisher_datestamp(rec),
        resource_status="active",
        metadata=metadata,
        oai_set=IVO_PUBLISHERS,
    )


def publishers_to_standard_records(
    publishers: list[PublisherRegistry],
) -> list[StandardRecord]:
    out = [publisher_standard_record(p) for p in publishers if p.oai_identifier.strip()]
    return sorted(out, key=lambda r: r.identifier)
