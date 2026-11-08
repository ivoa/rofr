"""Tombstone standards removed from ``STANDARDS_DIR`` but kept visible to harvesters."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from lxml import etree

from benson.oai.dates import normalize_datestamp

WITHDRAWN_STANDARDS_FILENAME = "withdrawn_standards.json"

RI_NS = "http://www.ivoa.net/xml/RegistryInterface/v1.0"
VSTD_NS = "http://www.ivoa.net/xml/StandardsRegExt/v1.0"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"


@dataclass(frozen=True)
class WithdrawnStandard:
    identifier: str
    withdrawn_at: str
    withdraw_reason: str | None = None


def withdrawn_manifest_path(standards_dir: Path) -> Path:
    return standards_dir / WITHDRAWN_STANDARDS_FILENAME


def _minimal_deleted_resource(identifier: str) -> etree._Element:
    """Stub ``ri:Resource`` for manifest-only tombstones (metadata not served over OAI)."""
    resource = etree.Element(
        f"{{{RI_NS}}}Resource",
        nsmap={
            "ri": RI_NS,
            "vstd": VSTD_NS,
            "xsi": XSI_NS,
        },
        attrib={
            f"{{{XSI_NS}}}type": "vstd:Standard",
            "status": "deleted",
        },
    )
    ident_el = etree.SubElement(resource, f"{{{RI_NS}}}identifier")
    ident_el.text = identifier
    title_el = etree.SubElement(resource, f"{{{RI_NS}}}title")
    title_el.text = identifier
    return resource


def load_withdrawn_manifest(path: Path) -> list[WithdrawnStandard]:
    if not path.is_file():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows = raw if isinstance(raw, list) else raw.get("standards", [])
    if not isinstance(rows, list):
        return []
    out: list[WithdrawnStandard] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        ident = (row.get("identifier") or "").strip()
        if not ident:
            continue
        withdrawn_at = normalize_datestamp(
            (row.get("withdrawn_at") or row.get("datestamp") or "").strip() or None
        )
        reason = row.get("withdraw_reason") or row.get("reason")
        if isinstance(reason, str):
            reason = reason.strip() or None
        else:
            reason = None
        out.append(
            WithdrawnStandard(
                identifier=ident,
                withdrawn_at=withdrawn_at,
                withdraw_reason=reason,
            )
        )
    return out


def manifest_tombstones_for_disk(
    standards_dir: Path,
    *,
    on_disk_identifiers: set[str],
) -> list[WithdrawnStandard]:
    """Withdrawn standards listed in the manifest but without a matching ``*.xml`` file."""
    entries = load_withdrawn_manifest(withdrawn_manifest_path(standards_dir))
    out: list[WithdrawnStandard] = []
    seen: set[str] = set()
    for entry in entries:
        if entry.identifier in on_disk_identifiers or entry.identifier in seen:
            continue
        seen.add(entry.identifier)
        out.append(entry)
    return out


def tombstone_metadata(identifier: str) -> etree._Element:
    return _minimal_deleted_resource(identifier)
