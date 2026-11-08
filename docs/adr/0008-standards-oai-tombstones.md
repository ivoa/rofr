# ADR 0008: OAI tombstones for withdrawn `ivo_managed` standards

## Status

Accepted

## Context

Benson publishes IVOA standard records from `assets/standards/` on **`GET /oai`** with `set=ivo_managed`. Operators add and edit one `*.xml` VOResource file per standard; there is no automated ingest.

The service declares **`deletedRecord=persistent`** in `Identify`, consistent with [Registry Interfaces](https://www.ivoa.net/documents/latest/RegistryInterface.html) §2.5 and [OAI-PMH](https://www.openarchives.org/OAI/openarchivesprotocol.html#DeletedRecords) §2.5.1. Harvesters that incrementally sync `ivo_managed` need **tombstones** (OAI header `status="deleted"`, no metadata) when a standard is delisted, not a silent disappearance of the identifier.

Publishing-registry **withdrawal** (`listing_status=withdrawn` in `publishers.json`) was implemented in Benson with explicit OAI tombstone behaviour and tests. **Managed standards** did not have an equivalent documented operator path until PR-D.

### Legacy parity caveat

The repository retains the legacy Java WAR for reference only. **It is unclear whether the historical Registry of Registries deployment reliably exposed OAI tombstones for withdrawn standards** in `ivo_managed`:

- Legacy behaviour for **removing** a standard XML file from the catalog (as opposed to editing it in place) is **not** documented in [regvalidate-functional-contract.md](../regvalidate-functional-contract.md) or [regvalidate-parity-notes.md](../regvalidate-parity-notes.md).
- We have **no** captured OAI responses showing a deleted `ivo://ivoa.net/std/…` header after file removal from the legacy standards tree.
- VOResource allows `status="deleted"` on the resource root; whether legacy code mapped that to OAI tombstones for RofR’s own `/oai` endpoint was **not** verified end-to-end against production archives.

Benson therefore treats persistent standards tombstones as a **spec-aligned product requirement**, not as a behaviour we can claim was proven on the old stack.

## Decision

1. **`status="deleted"` on a standard’s `*.xml`** — `StandardsStore` reads the root `status` attribute. OAI `ListRecords` / `GetRecord` emit a tombstone (no metadata), using `updated` as the OAI datestamp. The file may remain in the repo for audit.
2. **Removed `*.xml` files** — Operators list the IVOA identifier in [`withdrawn_standards.json`](../../assets/standards/withdrawn_standards.json) under `STANDARDS_DIR`. `StandardsStore` merges manifest-only entries as tombstones. If a file with the same identifier exists, the file wins.
3. **Operator documentation** — Withdrawal steps live in [`assets/standards/README.md`](../../assets/standards/README.md). Implementation: [`standards_withdrawn.py`](../../src/benson/registry/standards_withdrawn.py), loaded from [`standards_store.py`](../../src/benson/registry/standards_store.py).

No CLI for standards withdrawal (unlike `benson withdraw-publisher`); curation is edit-the-assets-and-commit.

## Consequences

- **Positive:** Incremental harvest of `ivo_managed` can observe delistings without a full reharvest, matching OAI `persistent` deletion semantics.
- **Positive:** Two operator paths (in-place `status="deleted"` vs file removal + manifest) mirror how Git-backed catalogs are usually maintained.
- **Negative:** Manifest and XML must stay consistent; duplicate or stale manifest rows are ignored when a live XML file exists.
- **Neutral:** Human-facing UIs do not list withdrawn standards; only OAI harvest consumers see tombstones (unlike publishers, there is no active-only JSON catalogue for standards).
- **Follow-up:** If legacy OAI captures surface showing different behaviour, update [regvalidate-parity-notes.md](../regvalidate-parity-notes.md) and either document intentional divergence or adjust implementation.
