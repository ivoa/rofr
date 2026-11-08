"""Load and index IVOA standard records from ``assets/standards``."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lxml import etree

from benson.config import Settings
from benson.oai.dates import normalize_datestamp
from benson.registry.registry_self import authority_record, ivoa_authority_record, registry_record
from benson.registry.standards_withdrawn import (
    manifest_tombstones_for_disk,
    tombstone_metadata,
    withdrawn_manifest_path,
)

@dataclass(frozen=True)
class StandardRecord:
    identifier: str
    datestamp: str
    resource_status: str
    metadata: etree._Element  # noqa: SLF001 — deep-copied ri:Resource root
    oai_set: str = "ivo_managed"


def _dir_mtime(path: Path) -> float:
    try:
        mtimes = [path.stat().st_mtime]
        manifest = withdrawn_manifest_path(path)
        if manifest.is_file():
            mtimes.append(manifest.stat().st_mtime)
        for child in path.glob("*.xml"):
            mtimes.append(child.stat().st_mtime)
        return max(mtimes)
    except OSError:
        return 0.0


def _find_direct(root: etree._Element, local_name: str) -> etree._Element | None:  # noqa: SLF001
    for el in root:
        tag = el.tag
        if not isinstance(tag, str):
            continue
        base = tag.rsplit("}", 1)[-1]
        if base == local_name:
            return el
    return None


def _parse_standard_file(path: Path) -> StandardRecord:
    parser = etree.XMLParser(no_network=True, resolve_entities=False)
    root = etree.parse(str(path), parser).getroot()
    ident_el = _find_direct(root, "identifier")
    if ident_el is None or not (ident_el.text and ident_el.text.strip()):
        msg = f"Missing identifier in {path.name}"
        raise ValueError(msg)
    updated = root.get("updated")
    status = root.get("status") or "active"
    metadata = etree.fromstring(
        etree.tostring(root, encoding="UTF-8"),
        parser=etree.XMLParser(no_network=True, resolve_entities=False),
    )
    return StandardRecord(
        identifier=ident_el.text.strip(),
        datestamp=normalize_datestamp(updated),
        resource_status=status,
        metadata=metadata,
    )


class StandardsStore:
    """In-memory index of standards XML files plus synthetic registry records."""

    def __init__(self, standards_dir: Path) -> None:
        self._standards_dir = standards_dir
        self._cache_mtime: float = -1.0
        self._records: list[StandardRecord] = []

    @classmethod
    def from_settings(cls, settings: Settings) -> StandardsStore:
        return cls(settings.standards_dir)

    def _reload_if_needed(self) -> None:
        mtime = _dir_mtime(self._standards_dir)
        if mtime == self._cache_mtime and self._records:
            return
        records: list[StandardRecord] = []
        if self._standards_dir.is_dir():
            for path in sorted(self._standards_dir.glob("*.xml")):
                records.append(_parse_standard_file(path))
            on_disk = {rec.identifier for rec in records}
            for entry in manifest_tombstones_for_disk(
                self._standards_dir, on_disk_identifiers=on_disk
            ):
                records.append(
                    StandardRecord(
                        identifier=entry.identifier,
                        datestamp=entry.withdrawn_at,
                        resource_status="deleted",
                        metadata=tombstone_metadata(entry.identifier),
                    )
                )
        self._records = records
        self._cache_mtime = mtime

    def standards(self) -> list[StandardRecord]:
        self._reload_if_needed()
        return list(self._records)

    def _synthetic_record(
        self, ident: str, datestamp: str, status: str, metadata: etree._Element
    ) -> StandardRecord:
        return StandardRecord(
            identifier=ident,
            datestamp=datestamp,
            resource_status=status,
            metadata=metadata,
        )

    def all_records(self, settings: Settings, base_url: str) -> list[StandardRecord]:
        """Registry and authority records first, then standards sorted by identifier."""
        self._reload_if_needed()
        out: list[StandardRecord] = []

        for ident, ds, st, md in (
            registry_record(settings, base_url),
            authority_record(settings, base_url),
            ivoa_authority_record(),
        ):
            out.append(self._synthetic_record(ident, ds, st, md))

        standards = sorted(self._records, key=lambda rec: rec.identifier)
        out.extend(standards)
        return out

    def get_by_identifier(
        self, settings: Settings, base_url: str, identifier: str
    ) -> StandardRecord | None:
        ident = identifier.strip()
        for rec in self.all_records(settings, base_url):
            if rec.identifier == ident:
                return rec
        return None
