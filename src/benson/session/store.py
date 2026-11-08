"""In-memory harvest run state keyed by ``run_id``."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from lxml import etree


@dataclass
class HarvestRun:
    run_id: str
    endpoint: str
    builtin_schemas: bool
    cache: bool
    show_status: str
    fmt: str
    error_fmt: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    oai_validation: etree._ElementTree | None = None  # noqa: SLF001
    ivoa_validation: etree._ElementTree | None = None
    vor_validation: etree._ElementTree | None = None
    merged_validation: etree._ElementTree | None = None
    resources: dict[str, bytes] = field(default_factory=dict)
    validated_resource: dict[str, etree._ElementTree] = field(default_factory=dict)
    status_rows: list[dict[str, str]] = field(default_factory=list)
    progress_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    background_task: asyncio.Task | None = None
    validation_error: str | None = None
    result_stub_url: str | None = None
    canceled: bool = False
    identify_oai_identifier: str | None = None
    identify_title: str | None = None

    def add_status_row(self, **kw: str) -> None:
        self.status_rows.append({k: str(v) for k, v in kw.items()})


class HarvestSessionStore:
    def __init__(self) -> None:
        self._runs: dict[str, HarvestRun] = {}
        self._lock = asyncio.Lock()

    async def create(self, run: HarvestRun) -> None:
        async with self._lock:
            self._runs[run.run_id] = run

    async def get(self, run_id: str) -> HarvestRun | None:
        async with self._lock:
            return self._runs.get(run_id)

    async def drop(self, run_id: str) -> None:
        async with self._lock:
            self._runs.pop(run_id, None)


store = HarvestSessionStore()
