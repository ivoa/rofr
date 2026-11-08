# IVOA standards catalog records

Default **`STANDARDS_DIR`**: VOResource **metadata records** for IVOA standards (one `*.xml` file per standard). These are **not** XSD schema files.

Served via Benson’s OAI-PMH endpoint (`GET /oai`, `set=ivo_managed`) and loaded by [`src/benson/registry/standards_store.py`](../../src/benson/registry/standards_store.py).

XSD validation of remote registries uses [`assets/schemas/`](../schemas/), not these files directly.

Full context: [`docs/schemas-and-validation-assets.md`](../../docs/schemas-and-validation-assets.md).

Design rationale (including legacy parity caveat): [ADR 0008](../../docs/adr/0008-standards-oai-tombstones.md).

## Adding or updating standards (manual)

There is **no automated ingest**: operators add or edit `*.xml` files here (and commit them). Each file is one standard record—a `ri:Resource` with an IVOA `identifier`, `title`, curation, references, and so on. Match the style of neighbouring files (for example [`adql.xml`](adql.xml)).

Set `updated` on the root element when the record changes; that value becomes the OAI **datestamp** for incremental harvest.

## Withdrawing a standard (OAI tombstones)

Benson advertises `deletedRecord=persistent` in `Identify`. Harvesters must still see identifiers for standards that are delisted. Use **one** of the following approaches.

### Option A — Keep the XML file, mark the resource deleted (preferred when you retain audit metadata)

1. Edit the standard’s `*.xml`.
2. On the root `ri:Resource`, set `status="deleted"` (VOResource semantics).
3. Set `updated` to the UTC time of withdrawal (this becomes the OAI **datestamp** for the tombstone).
4. Commit and deploy.

OAI responses use a **header** with `status="deleted"` and **no** `metadata` body, even though the file remains on disk. You may trim sensitive `content` / `capability` elements for clarity; they are not served while the record is deleted.

### Option B — Remove the XML file, list the identifier in the manifest

When the file should leave the tree entirely:

1. Note the record’s `ivo://…` **identifier** and withdrawal time.
2. Remove the `*.xml` file (or rename it out of this directory).
3. Add an entry to [`withdrawn_standards.json`](withdrawn_standards.json) in this directory:

```json
[
  {
    "identifier": "ivo://ivoa.net/std/Example",
    "withdrawn_at": "2026-11-08T19:00:00Z",
    "withdraw_reason": "optional operator note (not served in OAI)"
  }
]
```

4. Commit the manifest (and deletion of the XML) and deploy.

Manifest rows are **only** used when no `*.xml` with the same identifier is present. If a file still exists, the file wins (including `status="deleted"` on the file).

### Verifying tombstones

```bash
curl -sS 'http://localhost:8000/oai?verb=GetRecord&identifier=ivo%3A%2F%2Fivoa.net%2Fstd%2FExample&metadataPrefix=ivo_vor'
```

Expect `<header status="deleted">` and no `<metadata>` element.

Unlike publishing registries, withdrawn standards are **not** hidden from human-oriented JSON APIs—there is no active-only standards list on the home page. Tombstones matter for **OAI harvest** of `ivo_managed` only.
