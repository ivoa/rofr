"""Register a publishing registry after successful validation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from benson.config import Settings
from benson.registry.publishers_store import PublisherStore, normalize_endpoint
from benson.registry.registration_policy import eligible_for_registration, registration_blocked_by
from benson.service.rofr_lists import PublisherRegistry
from benson.session.store import HarvestRun, store


class RegistrationError(Exception):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(slots=True)
class RegistrationResult:
    record: PublisherRegistry
    created: bool


def _harvest_url(run: HarvestRun) -> str:
    return run.endpoint.strip().rstrip("/") or run.endpoint.strip()


def _live_check_fields(
    run: HarvestRun,
    oid: str,
    title: str,
    *,
    strict_identity: bool,
) -> tuple[str, str, str, str | None]:
    live_oai_identifier = (run.identify_oai_identifier or "").strip() or oid
    live_title = (run.identify_title or "").strip() or title
    if strict_identity:
        if not (run.identify_oai_identifier or "").strip():
            raise RegistrationError(
                "Identify response did not include a registry identifier.",
                status_code=409,
            )
        if live_oai_identifier != oid:
            raise RegistrationError(
                "Live identifier does not match registered registry.",
                status_code=409,
            )
        return live_oai_identifier, live_title, "ok", None

    check_status = "ok"
    check_detail = None
    if live_oai_identifier != oid:
        check_status = "identifier_mismatch"
        check_detail = f"live identifier is {live_oai_identifier}"
    return live_oai_identifier, live_title, check_status, check_detail


def _publisher_entry_dict(rec: PublisherRegistry) -> dict[str, object]:
    return {
        "oai_identifier": rec.oai_identifier,
        "title": rec.title,
        "harvest_access_url": rec.harvest_access_url,
        "registered_at": rec.registered_at,
        "updated_at": rec.updated_at,
    }


def update_blocked_reason(
    run: HarvestRun,
    existing: PublisherRegistry,
    endpoint_owner: PublisherRegistry | None,
) -> str | None:
    oid = existing.oai_identifier
    live_id = (run.identify_oai_identifier or "").strip()
    if not live_id:
        return "identify_identifier"
    if live_id != oid:
        return "identify_identifier_mismatch"
    if endpoint_owner is not None and endpoint_owner.oai_identifier != oid:
        return "endpoint_conflict"
    return None


def update_blocked_message(blocked_by: str, *, endpoint_owner: PublisherRegistry | None = None) -> str:
    if blocked_by == "identify_identifier":
        return (
            "Validation passed, but the Identify response did not include a registry identifier. "
            "Updates require a live identifier that matches the registered listing."
        )
    if blocked_by == "identify_identifier_mismatch":
        return (
            "Validation passed, but the live Identify identifier does not match the registered listing."
        )
    if blocked_by == "endpoint_conflict" and endpoint_owner is not None:
        return (
            f"OAI endpoint already registered as {endpoint_owner.oai_identifier}."
        )
    return "Update is not available for this validation run."


async def _register_new(
    run: HarvestRun,
    *,
    oid: str,
    title: str,
    pub_store: PublisherStore,
) -> RegistrationResult:
    existing = await pub_store.find_by_endpoint(run.endpoint)
    if existing is not None:
        raise RegistrationError(
            f"OAI endpoint already registered as {existing.oai_identifier}.",
            status_code=409,
        )

    now = datetime.now(UTC).isoformat()
    live_oai_identifier, live_title, check_status, check_detail = _live_check_fields(
        run, oid, title, strict_identity=False
    )
    record = PublisherRegistry(
        oai_identifier=oid,
        title=title,
        harvest_access_url=_harvest_url(run),
        registered_at=now,
        validation_run_id=run.run_id,
        last_checked_at=now,
        check_status=check_status,
        live_oai_identifier=live_oai_identifier,
        live_title=live_title,
        check_detail=check_detail,
    )
    stored = await pub_store.upsert(record)
    return RegistrationResult(record=stored, created=True)


async def _update_existing(
    run: HarvestRun,
    existing: PublisherRegistry,
    *,
    oid: str,
    title: str,
    pub_store: PublisherStore,
) -> RegistrationResult:
    endpoint_owner = await pub_store.find_by_endpoint(run.endpoint, exclude_identifier=oid)
    if endpoint_owner is not None:
        raise RegistrationError(
            f"OAI endpoint already registered as {endpoint_owner.oai_identifier}.",
            status_code=409,
        )

    live_oai_identifier, live_title, check_status, check_detail = _live_check_fields(
        run, oid, title, strict_identity=True
    )
    now = datetime.now(UTC).isoformat()
    record = PublisherRegistry(
        oai_identifier=oid,
        title=title,
        harvest_access_url=_harvest_url(run),
        registered_at=existing.registered_at,
        updated_at=now,
        validation_run_id=run.run_id,
        last_checked_at=now,
        check_status=check_status,
        live_oai_identifier=live_oai_identifier,
        live_title=live_title,
        check_detail=check_detail,
    )
    stored = await pub_store.upsert(record)
    return RegistrationResult(record=stored, created=False)


async def register_publisher(
    run_id: str,
    *,
    oai_identifier: str,
    title: str,
    settings: Settings,
) -> RegistrationResult:
    run = await store.get(run_id)
    if run is None:
        raise RegistrationError("Validation session not found or expired.", status_code=404)

    ok, reason, _nf, _nw = eligible_for_registration(run, settings)
    if not ok:
        raise RegistrationError(reason, status_code=409)

    oid = oai_identifier.strip()
    t = title.strip()
    if not oid:
        raise RegistrationError("IVOA identifier is required.")
    if not t:
        raise RegistrationError("Title is required.")

    pub_store = PublisherStore.from_settings(settings)
    await pub_store.ensure_seed()

    existing = await pub_store.find_by_identifier(oid)
    if existing is None:
        return await _register_new(run, oid=oid, title=t, pub_store=pub_store)
    return await _update_existing(run, existing, oid=oid, title=t, pub_store=pub_store)


async def eligibility_payload(run: HarvestRun, settings: Settings) -> dict[str, object]:
    ok, reason, nfail, nwarn = eligible_for_registration(run, settings)
    blocked_by = registration_blocked_by(run, settings)

    pub_store = PublisherStore.from_settings(settings)
    existing: PublisherRegistry | None = None
    mode = "create"
    suggest_id = (run.identify_oai_identifier or "").strip()
    if suggest_id:
        existing = await pub_store.find_by_identifier(suggest_id)
        if existing is not None:
            mode = "update"

    endpoint_changed = False
    if existing is not None and existing.harvest_access_url:
        endpoint_changed = normalize_endpoint(run.endpoint) != normalize_endpoint(existing.harvest_access_url)

    update_blocked_by: str | None = None
    endpoint_owner: PublisherRegistry | None = None
    if ok and existing is not None and mode == "update":
        endpoint_owner = await pub_store.find_by_endpoint(
            run.endpoint,
            exclude_identifier=existing.oai_identifier,
        )
        update_blocked_by = update_blocked_reason(run, existing, endpoint_owner)

    eligible = ok and update_blocked_by is None
    if ok and update_blocked_by:
        reason = update_blocked_message(update_blocked_by, endpoint_owner=endpoint_owner)

    return {
        "eligible": eligible,
        "reason": reason,
        "nfail": nfail,
        "nwarn": nwarn,
        "report_all_passed": nfail == 0 and nwarn == 0,
        "registration_blocked_by": blocked_by,
        "mode": mode,
        "existing_entry": _publisher_entry_dict(existing) if existing is not None else None,
        "endpoint_changed": endpoint_changed,
        "update_blocked_by": update_blocked_by,
        "endpoint": run.endpoint,
        "builtin_schemas": run.builtin_schemas,
        "suggested_oai_identifier": run.identify_oai_identifier,
        "suggested_title": run.identify_title,
    }
