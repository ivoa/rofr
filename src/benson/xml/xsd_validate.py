"""W3C XSD validation using bundled schemas under SCHEMA_ROOT."""

from __future__ import annotations

import copy
from pathlib import Path

from lxml import etree

from benson.xml.catalog import NAMESPACE_SCHEMA_FILES
from benson.xml.schema_resolver import (
    RI_NS,
    ivoa_bundle_schema,
    namespace_schema,
    oai_bundle_schema,
    schema_from_location,
)

OAI_NS = "http://www.openarchives.org/OAI/2.0/"
OAI_DC_NS = "http://www.openarchives.org/OAI/2.0/oai_dc/"
DC_NS = "http://purl.org/dc/elements/1.1/"
VOR_NS = "http://www.ivoa.net/xml/VOResource/v1.0"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"

_OAI_FOREIGN_HOLDERS = ("description", "metadata", "about")


def _collect_schema_errors(schema: etree.XMLSchema) -> list[str]:
    log = schema.error_log
    return [str(e) for e in log]


def _element_namespace(el: etree._Element) -> str | None:  # noqa: SLF001
    if el.tag.startswith("{"):
        return el.tag[1 : el.tag.index("}")]
    return el.nsmap.get(None)


def _schema_for_element(el: etree._Element, schema_root: Path) -> etree.XMLSchema | None:  # noqa: SLF001
    ns = _element_namespace(el)
    if not ns:
        return None
    root_key = str(schema_root.resolve())
    if ns.rstrip("/") == RI_NS.rstrip("/"):
        return ivoa_bundle_schema(root_key)
    return namespace_schema(root_key, ns)


def _validate_tree(el: etree._Element, schema: etree.XMLSchema) -> list[str]:  # noqa: SLF001
    if schema.validate(etree.ElementTree(el)):
        return []
    return _collect_schema_errors(schema)


def parse_schema_location(attr: str) -> list[tuple[str, str]] | None:
    """Split xsi:schemaLocation into namespace/schema URL pairs."""
    tokens = (attr or "").split()
    if len(tokens) % 2 != 0:
        return None
    return [(tokens[i], tokens[i + 1]) for i in range(0, len(tokens), 2)]


def declared_schema_url(el: etree._Element) -> str | None:  # noqa: SLF001
    """Return the schema URL paired with the element namespace in xsi:schemaLocation."""
    ns = _element_namespace(el)
    if not ns:
        return None
    loc_attr = el.get(f"{{{XSI_NS}}}schemaLocation")
    if not loc_attr:
        return None
    pairs = parse_schema_location(loc_attr)
    if pairs is None:
        return None
    ns_norm = ns.rstrip("/")
    for pair_ns, url in pairs:
        if pair_ns.rstrip("/") == ns_norm:
            return url
    return None


def validate_element_tree_declared(el: etree._Element, schema_root: Path) -> list[str]:  # noqa: SLF001
    """Validate a subtree using the schema declared in xsi:schemaLocation."""
    ns = _element_namespace(el)
    if not ns:
        return ["Element has no target namespace"]

    loc_attr = el.get(f"{{{XSI_NS}}}schemaLocation")
    if not loc_attr:
        return ["Missing xsi:schemaLocation (declared-schema mode)"]

    pairs = parse_schema_location(loc_attr)
    if pairs is None:
        return ["Malformed xsi:schemaLocation (odd number of tokens)"]

    schema_url = declared_schema_url(el)
    if schema_url is None:
        return [f"xsi:schemaLocation has no schema for namespace {ns}"]

    root_key = str(schema_root.resolve())
    schema = schema_from_location(root_key, schema_url)
    if schema is None:
        return [f"Cannot resolve declared schema location {schema_url!r}"]

    return _validate_tree(el, schema)


def _validate_oai_embedded_payloads_declared(root: etree._Element, schema_root: Path) -> list[str]:  # noqa: SLF001
    errors: list[str] = []
    for el in iter_oai_foreign_elements(root):
        ns = _element_namespace(el)
        if not ns:
            errors.append(f"Foreign OAI payload {el.tag!r} has no namespace")
            continue
        errors.extend(validate_element_tree_declared(el, schema_root))
    return errors


def _validate_oai_envelope_shell_declared(root: etree._Element, schema_root: Path) -> list[str]:  # noqa: SLF001
    schema_url = declared_schema_url(root)
    if schema_url is None:
        ns = _element_namespace(root) or OAI_NS
        if not root.get(f"{{{XSI_NS}}}schemaLocation"):
            return ["Missing xsi:schemaLocation (declared-schema mode)"]
        return [f"xsi:schemaLocation has no schema for namespace {ns}"]

    root_key = str(schema_root.resolve())
    schema = schema_from_location(root_key, schema_url)
    if schema is None:
        return [f"Cannot resolve declared schema location {schema_url!r}"]

    stubbed = _stub_oai_foreign_elements(root)
    return _validate_tree(stubbed, schema)


def iter_oai_foreign_elements(oai_root: etree._Element) -> list[etree._Element]:  # noqa: SLF001
    """Direct element children under oai:description, oai:metadata, and oai:about."""
    out: list[etree._Element] = []
    for tag in _OAI_FOREIGN_HOLDERS:
        for holder in oai_root.iterfind(f".//{{{OAI_NS}}}{tag}"):
            for child in holder:
                out.append(child)
    return out


def _stub_oai_foreign_elements(root: etree._Element) -> etree._Element:  # noqa: SLF001
    """Replace ##other payloads with minimal oai_dc for OAI envelope XSD."""
    stubbed = copy.deepcopy(root)
    for tag in _OAI_FOREIGN_HOLDERS:
        for holder in stubbed.iterfind(f".//{{{OAI_NS}}}{tag}"):
            for child in list(holder):
                holder.remove(child)
            dc_root = etree.Element(
                f"{{{OAI_DC_NS}}}dc",
                nsmap={"oai_dc": OAI_DC_NS, "dc": DC_NS},
            )
            title = etree.SubElement(dc_root, f"{{{DC_NS}}}title")
            title.text = "stub"
            holder.append(dc_root)
    return stubbed


def _validate_oai_embedded_payloads(root: etree._Element, schema_root: Path) -> list[str]:  # noqa: SLF001
    errors: list[str] = []
    for el in iter_oai_foreign_elements(root):
        ns = _element_namespace(el)
        if not ns:
            errors.append(f"Foreign OAI payload {el.tag!r} has no namespace")
            continue
        schema = _schema_for_element(el, schema_root)
        if schema is None:
            errors.append(f"No bundled schema for namespace {ns}")
            continue
        errors.extend(_validate_tree(el, schema))
    return errors


def _validate_oai_envelope_shell(root: etree._Element, schema_root: Path) -> list[str]:  # noqa: SLF001
    schema = oai_bundle_schema(str(schema_root.resolve()))
    stubbed = _stub_oai_foreign_elements(root)
    return _validate_tree(stubbed, schema)


def validate_oai_response_envelope(xml_bytes: bytes, schema_root: Path) -> list[str]:
    """Validate OAI-PMH 2.0 response: embedded payloads + OAI envelope structure."""
    parser = etree.XMLParser(no_network=True, resolve_entities=False, huge_tree=True)
    try:
        root = etree.fromstring(xml_bytes, parser)
    except etree.XMLSyntaxError as e:
        return [str(e)]
    ns = root.nsmap.get(None) or ""
    if root.tag.startswith("{"):
        ns = root.tag[1 : root.tag.index("}")]
    if ns != OAI_NS:
        return [f"Expected OAI-PMH root, got namespace {ns!r}"]

    errors: list[str] = []
    errors.extend(_validate_oai_embedded_payloads(root, schema_root))
    errors.extend(_validate_oai_envelope_shell(root, schema_root))
    return errors


def validate_oai_response_declared(xml_bytes: bytes, schema_root: Path) -> list[str]:
    """Validate OAI-PMH 2.0 response using declared xsi:schemaLocation on each part."""
    parser = etree.XMLParser(no_network=True, resolve_entities=False, huge_tree=True)
    try:
        root = etree.fromstring(xml_bytes, parser)
    except etree.XMLSyntaxError as e:
        return [str(e)]
    ns = root.nsmap.get(None) or ""
    if root.tag.startswith("{"):
        ns = root.tag[1 : root.tag.index("}")]
    if ns != OAI_NS:
        return [f"Expected OAI-PMH root, got namespace {ns!r}"]

    errors: list[str] = []
    errors.extend(_validate_oai_embedded_payloads_declared(root, schema_root))
    errors.extend(_validate_oai_envelope_shell_declared(root, schema_root))
    return errors


def validate_full_doc(xml_bytes: bytes, schema_root: Path) -> list[str]:
    """Validate a full XML document with the appropriate bundled schema (OAI or VOR)."""
    parser = etree.XMLParser(no_network=True, resolve_entities=False, huge_tree=True)
    try:
        root = etree.fromstring(xml_bytes, parser)
    except etree.XMLSyntaxError as e:
        return [str(e)]

    ns = root.nsmap.get(None) or (root.tag[1:].split("}", 1)[0] if root.tag.startswith("{") else "")
    if ns == OAI_NS:
        return validate_oai_response_envelope(xml_bytes, schema_root)

    if ns == VOR_NS or ns in NAMESPACE_SCHEMA_FILES:
        schema = _schema_for_element(root, schema_root)
        if schema is None:
            return []
        return _validate_tree(root, schema)

    return []


def validate_element_tree(el: etree._Element, schema_root: Path) -> list[str]:  # noqa: SLF001
    """Validate a subtree by target namespace URI."""
    ns = _element_namespace(el)
    if not ns:
        return []

    schema = _schema_for_element(el, schema_root)
    if schema is None:
        return [f"No bundled schema for namespace {ns}"]

    return _validate_tree(el, schema)


def iter_oai_metadata_elements(oai_root: etree._Element) -> list[etree._Element]:  # noqa: SLF001
    """First element children under oai:metadata for ListRecords/ListIdentifiers fragments."""
    out: list[etree._Element] = []
    for md in oai_root.iterfind(f".//{{{OAI_NS}}}metadata"):
        for child in md:
            out.append(child)
    return out
