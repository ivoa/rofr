# Benson — implementation backlog

PR-sized work items for Benson after core OAI publishing on `/oai`. Normative checklist: [`.cursor/skills/ivoa-registry-of-registries/requirements.md`](../.cursor/skills/ivoa-registry-of-registries/requirements.md).

---

## Done (reference)

| Area | Notes |
|------|--------|
| **`GET` / `POST` `/oai`** | Six verbs, `text/xml`, resumption, `from`/`until`, standard error codes |
| **`ivo_managed` / `ivo_publishers`** | Sets on `/oai`; publishers from `publishers.json` |
| **Harvest validator** | Phases 1–3, registration, publishers JSON API (see [functional contract](regvalidate-functional-contract.md)) |
| **Publisher Identify XML** | `identify_resource_xml` in `publishers.json` ([publisher-oai-metadata.md](publisher-oai-metadata.md)) |
| **Publisher withdraw** | CLI `withdraw-publisher` / `reactivate-publisher`; OAI tombstones; [publisher-oai-metadata.md](publisher-oai-metadata.md) |
| **Withdrawn standards (`ivo_managed`)** | `status="deleted"` on standard XML and/or [`withdrawn_standards.json`](../assets/standards/withdrawn_standards.json); [assets/standards/README.md](../assets/standards/README.md); [ADR 0008](adr/0008-standards-oai-tombstones.md) |
| **Searchables / publishers UI** | Home page lists (RegTAP/cache + `publishers.json`) |
| **Production OAI / proxy** | [production-oai.md](production-oai.md) |
| **Compliance audit (PR-H)** | [compliance.md](compliance.md) (+ links from production-oai, README Deployers) |

Harvest URLs: [docs/README.md § OAI endpoints](README.md#oai-endpoints).

---

## Open items (one PR each)

### PR-I — Validator / parity (scoped)

Pick **one** gap per PR from [regvalidate-parity-notes.md](regvalidate-parity-notes.md) (e.g. phase 1 explorer wiring, phase 3 limits, JSON compat). Not OAI-publisher work; keep PRs narrow.

---

## Won’t do (unless explicitly requested)

- **Separate CGI-style catalogue routes** (`/list-publishers`, `/list-searchables`, etc.) — harvest and machine catalogues use **`/oai`**; searchables use RegTAP/cache on the home page.
- **In-repo VO harvest client** for Note §3 — Benson publishes OAI; harvesters are external.
- **SOAP harvest** — out of scope (RI / Note).
