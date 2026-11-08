"""Operator withdraw and reactivate flows for registered publishing registries."""

from __future__ import annotations

from benson.registry.publishers_store import PublisherStore
from benson.service.rofr_lists import PublisherRegistry


class PublisherLifecycleError(Exception):
    pass


async def withdraw_publisher(
    store: PublisherStore,
    oai_identifier: str,
    *,
    reason: str | None = None,
    dry_run: bool = False,
) -> PublisherRegistry:
    try:
        return await store.withdraw(oai_identifier, reason=reason, dry_run=dry_run)
    except ValueError as exc:
        raise PublisherLifecycleError(str(exc)) from exc
    except LookupError as exc:
        raise PublisherLifecycleError(str(exc)) from exc


async def reactivate_publisher(
    store: PublisherStore,
    oai_identifier: str,
    *,
    dry_run: bool = False,
) -> PublisherRegistry:
    try:
        return await store.reactivate(oai_identifier, dry_run=dry_run)
    except ValueError as exc:
        raise PublisherLifecycleError(str(exc)) from exc
    except LookupError as exc:
        raise PublisherLifecycleError(str(exc)) from exc
