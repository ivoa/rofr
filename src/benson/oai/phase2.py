"""Phase 2: Four fixed OAI GET validations + XSD + checkIVOAOAI."""

from __future__ import annotations

import httpx
from lxml import etree

from benson.config import Settings
from benson.oai.client import fetch_oai
from benson.xml import results as R
from benson.xml import xslt_eval
from benson.xml import xsd_validate

OAI_NS = "http://www.openarchives.org/OAI/2.0/"
RI_NS = "http://www.ivoa.net/xml/RegistryInterface/v1.0"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"

IVOA_CHECKS: tuple[tuple[str, str], ...] = (
    ("Identify", "verb=Identify"),
    ("ListMetadataFormats", "verb=ListMetadataFormats"),
    ("ListSets", "verb=ListSets"),
    ("ListRecords", "verb=ListRecords&metadataPrefix=ivo_vor&set=ivo_managed"),
)


def _failure_message(role: str) -> str:
    match role:
        case "Identify":
            return "Service must respond to a legal OAI Identify query."
        case "ListMetadataFormats":
            return "Service must respond to a legal OAI ListMetadataFormats query."
        case "ListSets":
            return "Service must respond to a legal OAI ListSets query."
        case _:
            return (
                "Service must respond to a legal OAI ListRecords query "
                "(and support the 'ivo_vor' metadata prefix and the 'ivo_managed' set)."
            )


_XPATH_NS = {"oai": OAI_NS, "ri": RI_NS, "xsi": XSI_NS}


def _resource_child_text(reg: etree._Element, local_name: str) -> str:  # noqa: SLF001
    for child in reg:
        if etree.QName(child).localname == local_name and child.text:
            return child.text.strip()
    return ""


def extract_identify_state(parsed: etree._Element) -> dict[str, str]:  # noqa: SLF001
    """Parse registry metadata from an Identify response."""
    registry_id = ""
    title = ""
    managed: list[str] = []
    for reg in parsed.xpath(
        ".//oai:Identify/oai:description/ri:Resource[contains(@xsi:type, ':Registry')]",
        namespaces=_XPATH_NS,
    ):
        if not registry_id:
            registry_id = _resource_child_text(reg, "identifier")
        if not title:
            title = _resource_child_text(reg, "title")
        for ma in reg.findall(f"{{{RI_NS}}}managedAuthority"):
            if ma.text and ma.text.strip():
                managed.append(ma.text.strip())
        if not managed:
            for child in reg:
                if etree.QName(child).localname == "managedAuthority" and child.text:
                    managed.append(child.text.strip())
    if not registry_id:
        oai_id_el = parsed.find(f".//{{{OAI_NS}}}Identify/{{{OAI_NS}}}identifier")
        if oai_id_el is not None and oai_id_el.text:
            registry_id = oai_id_el.text.strip()
    if not title:
        repo_el = parsed.find(f".//{{{OAI_NS}}}Identify/{{{OAI_NS}}}repositoryName")
        if repo_el is not None and repo_el.text:
            title = repo_el.text.strip()
    managed_ids = "/" + "/".join(managed) + "/" if managed else "//"
    return {
        "registryID": registry_id,
        "managedAuthorityIDs": managed_ids,
        "registrationIdentifier": registry_id,
        "registrationTitle": title,
    }


def identify_registration_defaults(parsed: etree._Element) -> dict[str, str]:  # noqa: SLF001
    """Return suggested registration form values from an Identify response."""
    state = extract_identify_state(parsed)
    out: dict[str, str] = {}
    if state["registrationIdentifier"]:
        out["oai_identifier"] = state["registrationIdentifier"]
    if state["registrationTitle"]:
        out["title"] = state["registrationTitle"]
    return out


async def build_ivoa_harvest_validation(
    client: httpx.AsyncClient,
    endpoint: str,
    show_status: str,
    *,
    timeout: float,
    builtin_schemas: bool,
    settings: Settings,
) -> tuple[etree._Element, dict[str, str], dict[str, str]]:
    root = R.harvest_validation_root(endpoint.rstrip(), show_status)

    check_xsl = settings.assets_root / "checkIVOAOAI.xsl"
    identify_state: dict[str, str] = {}
    registration_defaults: dict[str, str] = {}

    for role, qp in IVOA_CHECKS:
        qp_body = qp.lstrip().lstrip("?")
        status, raw, codes, parse_err = await fetch_oai(client, endpoint, qp_body, timeout=timeout)

        tq = etree.SubElement(root, "testQuery", name=role, options=qp, role=role)

        http_ok = 200 <= status < 300
        if not http_ok:
            tq.append(R.ri_test(False, f"{_failure_message(role)} (HTTP {status})"))
            continue

        if parse_err:
            tq.append(R.ri_test(False, f"{parse_err}"))
            continue

        violations: list[str] = []
        if builtin_schemas:
            violations.extend(xsd_validate.validate_oai_response_envelope(raw, settings.schema_root))
        else:
            violations.extend(xsd_validate.validate_oai_response_declared(raw, settings.schema_root))

        try:
            parsed = etree.fromstring(raw, etree.XMLParser(no_network=True, resolve_entities=False))
        except etree.XMLSyntaxError as exc:
            tq.append(R.ri_test(False, str(exc)))
            continue

        if role == "Identify":
            identify_state = extract_identify_state(parsed)
            registration_defaults = identify_registration_defaults(parsed)

        used_xslt = False
        if violations:
            tq.append(
                R.ri_test(
                    False,
                    "; ".join(violations[:3]) + ("…" if len(violations) > 3 else ""),
                ),
            )
            continue

        if check_xsl.is_file():
            xsl_params: dict[str, str] = {"expectError": "false"}
            if role == "ListRecords" and identify_state:
                xsl_params.update(identify_state)
            try:
                xout = xslt_eval.transform(
                    check_xsl,
                    parsed,
                    params=xsl_params,
                )
                for child in xout.getroot():
                    used_xslt = True
                    tq.append(child)
            except Exception:
                used_xslt = False

        if not used_xslt:
            ri_ok = not codes
            msg = "OK" if ri_ok else _failure_message(role)
            tq.append(R.ri_test(ri_ok, msg))

    return root, registration_defaults, identify_state
