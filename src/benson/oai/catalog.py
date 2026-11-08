"""Load publisher holdings for the OAI-PMH server."""

from __future__ import annotations

from benson.config import Settings
from benson.registry.publisher_oai import publishers_to_standard_records
from benson.registry.publishers_store import PublisherStore
from benson.registry.standards_store import StandardRecord


async def load_publisher_oai_records(settings: Settings) -> list[StandardRecord]:
    store = PublisherStore.from_settings(settings)
    await store.ensure_seed()
    rows = await store.load()
    return publishers_to_standard_records(rows)
