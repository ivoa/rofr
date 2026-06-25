"""JSON-backed store for registered publishing registries."""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from benson.config import Settings
from benson.service.rofr_lists import PublisherRegistry

_CHECK_FIELD_KEYS = (
    "last_checked_at",
    "check_status",
    "live_oai_identifier",
    "live_title",
    "check_detail",
)

_LOCKS: dict[str, asyncio.Lock] = {}


def _lock_for(path: Path) -> asyncio.Lock:
    key = str(path.resolve())
    if key not in _LOCKS:
        _LOCKS[key] = asyncio.Lock()
    return _LOCKS[key]


def normalize_endpoint(url: str) -> str:
    u = url.strip().rstrip("/")
    if u.endswith("?"):
        u = u[:-1].rstrip("/")
    return u.lower()


@dataclass(slots=True)
class StoredPublisher:
    oai_identifier: str
    title: str
    harvest_access_url: str
    registered_at: str
    updated_at: str | None = None
    validation_run_id: str | None = None
    last_checked_at: str | None = None
    check_status: str | None = None
    live_oai_identifier: str | None = None
    live_title: str | None = None
    check_detail: str | None = None

    def to_registry(self) -> PublisherRegistry:
        return PublisherRegistry(
            oai_identifier=self.oai_identifier,
            title=self.title,
            harvest_access_url=self.harvest_access_url,
            registered_at=self.registered_at,
            updated_at=self.updated_at,
            validation_run_id=self.validation_run_id,
            last_checked_at=self.last_checked_at,
            check_status=self.check_status,
            live_oai_identifier=self.live_oai_identifier,
            live_title=self.live_title,
            check_detail=self.check_detail,
        )

    @classmethod
    def from_registry(cls, rec: PublisherRegistry) -> StoredPublisher:
        if not rec.harvest_access_url:
            raise ValueError("harvest_access_url is required")
        return cls(
            oai_identifier=rec.oai_identifier,
            title=rec.title,
            harvest_access_url=rec.harvest_access_url,
            registered_at=rec.registered_at or datetime.now(UTC).isoformat(),
            updated_at=rec.updated_at,
            validation_run_id=rec.validation_run_id,
            last_checked_at=rec.last_checked_at,
            check_status=rec.check_status,
            live_oai_identifier=rec.live_oai_identifier,
            live_title=rec.live_title,
            check_detail=rec.check_detail,
        )


class PublisherStore:
    def __init__(self, registry_file: Path) -> None:
        self._path = registry_file.resolve()
        self._path.parent.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_settings(cls, settings: Settings) -> PublisherStore:
        return cls(settings.publishers_registry_file)

    def _empty_document(self) -> dict:
        return {"version": 1, "publishers": []}

    def _read_document_unlocked(self) -> dict:
        if not self._path.is_file():
            return self._empty_document()
        text = self._path.read_text(encoding="utf-8").strip()
        if not text:
            return self._empty_document()
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("publishers registry must be a JSON object")
        data.setdefault("version", 1)
        data.setdefault("publishers", [])
        return data

    def _write_document_unlocked(self, data: dict) -> None:
        tmp = self._path.with_suffix(".json.tmp")
        payload = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        tmp.write_text(payload, encoding="utf-8")
        os.replace(tmp, self._path)

    async def load(self) -> list[PublisherRegistry]:
        async with _lock_for(self._path):
            doc = self._read_document_unlocked()
        out: list[PublisherRegistry] = []
        for row in doc.get("publishers", []):
            if not isinstance(row, dict):
                continue
            oid = (row.get("oai_identifier") or "").strip()
            title = (row.get("title") or "").strip()
            url = (row.get("harvest_access_url") or "").strip() or None
            if not oid:
                continue
            out.append(
                PublisherRegistry(
                    oai_identifier=oid,
                    title=title or oid,
                    harvest_access_url=url,
                    registered_at=row.get("registered_at"),
                    updated_at=row.get("updated_at"),
                    validation_run_id=row.get("validation_run_id"),
                    last_checked_at=row.get("last_checked_at"),
                    check_status=row.get("check_status"),
                    live_oai_identifier=row.get("live_oai_identifier"),
                    live_title=row.get("live_title"),
                    check_detail=row.get("check_detail"),
                )
            )
        return out

    async def find_by_endpoint(
        self,
        url: str,
        *,
        exclude_identifier: str | None = None,
    ) -> PublisherRegistry | None:
        norm = normalize_endpoint(url)
        exclude = (exclude_identifier or "").strip()
        for rec in await self.load():
            if exclude and rec.oai_identifier == exclude:
                continue
            if rec.harvest_access_url and normalize_endpoint(rec.harvest_access_url) == norm:
                return rec
        return None

    async def find_by_identifier(self, oai_identifier: str) -> PublisherRegistry | None:
        key = oai_identifier.strip()
        for rec in await self.load():
            if rec.oai_identifier == key:
                return rec
        return None

    async def upsert(self, record: PublisherRegistry) -> PublisherRegistry:
        stored = StoredPublisher.from_registry(record)
        async with _lock_for(self._path):
            doc = self._read_document_unlocked()
            rows = doc.setdefault("publishers", [])
            replaced = False
            for i, row in enumerate(rows):
                if not isinstance(row, dict):
                    continue
                if (row.get("oai_identifier") or "").strip() == stored.oai_identifier:
                    new_row = asdict(stored)
                    for key in _CHECK_FIELD_KEYS:
                        if row.get(key) is not None and new_row.get(key) is None:
                            new_row[key] = row[key]
                    rows[i] = new_row
                    replaced = True
                    break
            if not replaced:
                rows.append(asdict(stored))
            self._write_document_unlocked(doc)
        return stored.to_registry()

    async def annotate_checks(self, results) -> None:
        from benson.registry.publishers_check import PublisherCheckResult  # noqa: PLC0415

        by_id: dict[str, PublisherCheckResult] = {r.oai_identifier: r for r in results}
        async with _lock_for(self._path):
            doc = self._read_document_unlocked()
            rows = doc.setdefault("publishers", [])
            for row in rows:
                if not isinstance(row, dict):
                    continue
                oid = (row.get("oai_identifier") or "").strip()
                result = by_id.get(oid)
                if result is None:
                    continue
                row["last_checked_at"] = result.checked_at
                row["check_status"] = result.status
                row["live_oai_identifier"] = result.live_oai_identifier
                row["live_title"] = result.live_title
                row["check_detail"] = result.detail
            self._write_document_unlocked(doc)

    async def ensure_seed(self) -> None:
        async with _lock_for(self._path):
            if not self._path.is_file():
                self._write_document_unlocked(self._empty_document())
