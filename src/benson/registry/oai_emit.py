"""Emit OAI-PMH ListRecords XML from publisher registry records."""

from __future__ import annotations

from lxml import etree

from benson.registry.publisher_oai import build_publisher_metadata
from benson.service.rofr_lists import PublisherRegistry

OAI_NS = "http://www.openarchives.org/OAI/2.0/"


def publishers_to_list_records_xml(records: list[PublisherRegistry]) -> bytes:
    """Build a legacy ListRecords fragment (no OAI envelope) for publisher rows."""
    root = etree.Element(
        f"{{{OAI_NS}}}OAI-PMH",
        nsmap={"oai": OAI_NS},
    )
    list_records = etree.SubElement(root, f"{{{OAI_NS}}}ListRecords")
    for rec in records:
        oai_rec = etree.SubElement(list_records, f"{{{OAI_NS}}}record")
        header = etree.SubElement(oai_rec, f"{{{OAI_NS}}}header")
        ident = etree.SubElement(header, f"{{{OAI_NS}}}identifier")
        ident.text = rec.oai_identifier
        metadata = etree.SubElement(oai_rec, f"{{{OAI_NS}}}metadata")
        metadata.append(build_publisher_metadata(rec))
    return etree.tostring(
        root,
        encoding="UTF-8",
        xml_declaration=True,
        pretty_print=True,
    )
