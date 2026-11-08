# Benson — implementation backlog

PR-sized work items for Benson after core OAI publishing on `/oai`. Normative checklist: [`.cursor/skills/ivoa-registry-of-registries/requirements.md`](../.cursor/skills/ivoa-registry-of-registries/requirements.md).

---

## Done (reference)

| Area | Notes |
|------|--------|
| **`GET` / `POST` `/oai`** | Six verbs, `text/xml`, resumption, `from`/`until`, standard error codes |
| **`ivo_managed` / `ivo_publishers`** | Sets on `/oai`; publishers from `publishers.json` |
| **`GET /list-publishers`** | Full OAI envelope; same rows as `ListRecords&set=ivo_publishers` |
| **Harvest validator** | Phases 1–3, registration, publishers JSON API (see [functional contract](regvalidate-functional-contract.md)) |
| **Publisher Identify XML** | `identify_resource_xml` in `publishers.json` ([publisher-oai-metadata.md](publisher-oai-metadata.md)) |
| **Publisher withdraw** | CLI `withdraw-publisher` / `reactivate-publisher`; OAI tombstones; [publisher-oai-metadata.md](publisher-oai-metadata.md) |

Harvest URLs: [docs/README.md § OAI endpoints](README.md#oai-endpoints).

---

## Open items (one PR each)

### PR-D — Deleted or removed standards in `ivo_managed`

- When a standard XML file is removed or marked inactive, expose a tombstone in List/Get responses (persistent deletion policy already declared in Identify).
- Optional: watcher or explicit manifest for withdrawn standards.

### PR-E — `/list-publishers` parity sample

- Add `docs/samples/list-publishers/` fixture(s) and a short README.
- Optional replay test comparing envelope shape to legacy `rofr.ivoa.net` if a capture is available.

### PR-F — `GET /list-searchables` catalog

- Replace 501 stub in `src/benson/http/catalog.py` with an OAI or HTML catalog of searchable registries (RegTAP/cache), or document intentional omission and remove the route.
- Align with RofR Note §4.3 scope decision in an ADR if behaviour differs from legacy.

### PR-G — Deployer docs: public `baseURL` behind proxies

- Document `BENSON_PROXY_HEADERS`, `FORWARDED_ALLOW_IPS`, and verification steps so `Identify` `baseURL` matches the URL harvesters use.
- Add a short “production OAI” subsection to README or docs/README.

### PR-H — Requirements compliance audit

- Walk [requirements.md](../.cursor/skills/ivoa-registry-of-registries/requirements.md) §1–§8; check off implemented items with test/doc links.
- File issues for any intentional non-compliance.

### PR-I — Validator / parity (scoped)

Pick **one** gap per PR from [regvalidate-parity-notes.md](regvalidate-parity-notes.md) (e.g. phase 1 explorer wiring, phase 3 limits, JSON compat). Not OAI-publisher work; keep PRs narrow.

---

## Won’t do (unless explicitly requested)

- **`/list-publishers` as full OAI verb dispatcher** — canonical base is `/oai`; legacy path stays ListRecords-shaped.
- **In-repo VO harvest client** for Note §3 — Benson publishes OAI; harvesters are external.
- **SOAP harvest** — out of scope (RI / Note).
