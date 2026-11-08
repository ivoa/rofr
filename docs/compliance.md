# Benson compliance and normativity

This page records how the **Benson** deployment maps to IVOA RofR / Registry Interfaces / OAI-PMH, what is **LOCAL** (Benson or operator choice only), and where to find tests. It augments [production-oai.md](production-oai.md) and the full checklist in [requirements.md](../.cursor/skills/ivoa-registry-of-registries/requirements.md).

**Legend:** `MUST` · `SHOULD` · `NOTE` (RofR Note) · `LOCAL` (not IVOA normative). Narrative: [reference.md](../.cursor/skills/ivoa-registry-of-registries/reference.md). Known spec tensions: [reference.md § Known ambiguities](../.cursor/skills/ivoa-registry-of-registries/reference.md#known-ambiguities-flag-do-not-silently-resolve).

---

## 1. Scope and role

| Topic | Status | Evidence / doc |
|-------|--------|----------------|
| RofR as publishing registry (not end-user search) | **Documented** | [README](../README.md), [docs/README § validation](README.md) |
| Primary OAI clients are harvesters | **Documented** | [docs/README § OAI](README.md#oai-endpoints), Note §3 recipe in [reference.md](../.cursor/skills/ivoa-registry-of-registries/reference.md) |
| Not a mandatory HA “master” registry | **Documented** | Note §3.1; no uptime SLA in docs |
| Searchable list via RegTAP (optional UI) | **LOCAL / NOTE §4.3** | Home page; [searchables_regtap.py](../src/benson/service/searchables_regtap.py); not OAI |
| No in-repo VO harvest client | **Out of scope** | [implementation-todo.md § Won’t do](implementation-todo.md) |
| No SOAP harvest | **Out of scope** | RI HTTP-only for new work |

---

## 2. OAI-PMH publisher (`/oai`)

| Topic | Status | Evidence |
|-------|--------|----------|
| GET and POST | **Implemented** | `test_oai_post_identify` in [test_standards_oai.py](../tests/test_standards_oai.py) |
| Six verbs, standard error codes | **Implemented** | [test_standards_oai.py](../tests/test_standards_oai.py), [test_registry.py](../tests/test_registry.py), [oai/server.py](../src/benson/oai/server.py) |
| `oai_dc` and `ivo_vor` | **Implemented** | `test_oai_ivo_publishers_list_records_oai_dc`, ListMetadataFormats via phase 2 tests |
| Sets `ivo_managed`, `ivo_publishers` | **Implemented** | `test_list_sets_includes_ivo_publishers`, publisher/standards ListRecords tests |
| Identify + embedded `vg:Registry` | **Implemented** | `test_identify_validates_oai_envelope`, [registry_self.py](../src/benson/registry/registry_self.py) |
| `deletedRecord=persistent`, tombstones | **Implemented** | [test_publisher_lifecycle.py](../tests/test_publisher_lifecycle.py), [test_standards_withdrawn.py](../tests/test_standards_withdrawn.py) |
| Resumption tokens | **Implemented** | `test_oai_resumption_walks_pages` |
| `from` / `until` filtering | **Implemented** | OAI server date logic; extend tests as needed |
| **`baseURL` matches public URL** | **Operator-dependent** | [production-oai.md](production-oai.md) (`BENSON_PROXY_HEADERS`, `FORWARDED_ALLOW_IPS`) — **LOCAL** |
| Standards (`vstd:Standard`) in `ivo_managed` | **Implemented** | [assets/standards/](../assets/standards/), standards OAI tests |
| Publishers in `ivo_publishers` from `publishers.json` | **Implemented** | [publisher-oai-metadata.md](publisher-oai-metadata.md), [test_registry.py](../tests/test_registry.py) |

**Harvest example (normative recipe):**

```http
GET /oai?verb=ListRecords&metadataPrefix=ivo_vor&set=ivo_publishers
```

---

## 3. Registry discovery (harvester behaviour)

Benson **publishes** the publisher list; it does **not** implement the Note §3 harvest client. Document expected client behaviour in [reference.md](../.cursor/skills/ivoa-registry-of-registries/reference.md) § Registry discovery. No automated test in this repo for external harvest loops.

---

## 4. Registration and validation

| Topic | Status | Evidence |
|-------|--------|----------|
| HTTP GET OAI endpoint validation | **Implemented** | [regvalidate-functional-contract.md](regvalidate-functional-contract.md), harvest tests |
| Phases 1–3 + standalone VOR | **Implemented** | [test_standards_oai.py](../tests/test_standards_oai.py), [test_validate_one_voresource.py](../tests/test_validate_one_voresource.py) |
| Policy env (`REGISTRATION_MAX_*`, builtin schemas) | **LOCAL** | [README § Environment](../README.md#environment) |
| Registration + update + hijack checks | **Implemented** | [test_registry.py](../tests/test_registry.py) |
| `endpoint` trailing `?` / `&` | **LOCAL parity** | [test_oai_urls.py](../tests/test_oai_urls.py), contract §2.2 |
| Endpoint change without re-validation auth | **Underspecified in IVOA** | Note §4.4; Benson uses re-validation on update — see README |

**Phase 1** may depend on external OAI Repository Explorer / `comply` when configured — deployment-specific.

---

## 5. Operational endpoints (LOCAL surface)

| Route / command | Doc |
|-----------------|-----|
| `GET`/`POST` `/oai` | [README](../README.md), [docs/README](README.md) |
| `GET /api/v1/registry/publishers` | README |
| `/validator`, `/regvalidate`, jobs API | README, [regvalidate-functional-contract.md](regvalidate-functional-contract.md) |
| `benson check-publishers` | README § Deployers |
| `benson sync-searchables` | README § Docker |

**Removed pre-release (intentional):** `/list-publishers`, `/list-searchables` CGI-style shortcuts — [implementation-todo.md](implementation-todo.md).

---

## 6. Errors and safety

| Topic | Status | Evidence |
|-------|--------|----------|
| OAI XML errors (no invented codes) | **Implemented** | [oai/server.py](../src/benson/oai/server.py) |
| No stack traces on OAI (`BENSON_EXPOSE_ERRORS`) | **LOCAL** | [error_handlers.py](../src/benson/http/error_handlers.py), README |
| Registration identifier mismatch rejected | **Implemented** | `test_update_blocked_by_identify_mismatch` |

---

## 7. Documentation deliverables

| Deliverable | Location |
|-------------|----------|
| Endpoint tables | [README](../README.md), [docs/README](README.md) |
| OAI curl examples | [docs/README § OAI](README.md#oai-endpoints), [production-oai.md](production-oai.md) |
| LOCAL / proxy behaviour | [production-oai.md](production-oai.md) (this page, [reference.md](../.cursor/skills/ivoa-registry-of-registries/reference.md)) |
| Ambiguities | [reference.md § Known ambiguities](../.cursor/skills/ivoa-registry-of-registries/reference.md#known-ambiguities-flag-do-not-silently-resolve) |
| Validator contract | [regvalidate-functional-contract.md](regvalidate-functional-contract.md) |

---

## 8. Tests and evidence

Run: `pytest` (see [README § Tests](../README.md#tests)). Parity fixtures: [docs/samples/](samples/), [regvalidate-parity-notes.md](regvalidate-parity-notes.md).

| Area | Primary tests |
|------|----------------|
| OAI verbs / sets / resumption | `tests/test_standards_oai.py`, `tests/test_registry.py`, `tests/test_standards_withdrawn.py` |
| Publisher lifecycle | `tests/test_publisher_lifecycle.py` |
| Validator / jobs | `tests/test_validation_job.py`, `tests/test_validator_jobs.py` |
| Phase 3 harvest | `tests/test_phase3_harvest.py` |

---

## LOCAL and non-IVOA elements (operator reference)

These are **not** OAI or RofR Note requirements; they exist for Benson deployment, parity, or convenience.

| Item | Purpose | Doc |
|------|---------|-----|
| `BENSON_PROXY_HEADERS`, `FORWARDED_ALLOW_IPS` | Public `baseURL` behind reverse proxy | [production-oai.md](production-oai.md) |
| No `OAI_PUBLIC_URL` env | URLs derived from request + forwarded headers | [production-oai.md](production-oai.md) |
| `REGISTRATION_MAX_FAILURES`, `REGISTRATION_MAX_WARNINGS`, `REGISTRATION_REQUIRE_BUILTIN_SCHEMAS` | Admission policy | README |
| `SEARCHABLES_*` / RegTAP cache | Optional searchable registry UI | README, `searchables_regtap.py` |
| JSON publishers API | UI and operators | README |
| Async validator jobs | Modern UI | README |
| `/regvalidate` alias | Legacy path | README |
| Pseudo-JSON harvest API | Legacy parity | [regvalidate-parity-notes.md](regvalidate-parity-notes.md) |
| `BENSON_PARITY_JSON`, `BENSON_EXPOSE_ERRORS` | Debug / parity | README |

---

## Open gaps (documented; track in issues if needed)

| Gap | Notes |
|-----|--------|
| Formal harvest client for Note §3 | **Won’t do** in-repo |
| Legacy set name `ivoa_publishers` | Benson uses **`ivo_publishers`**; legacy CGI used `ivoa_publishers` — see ambiguity #1 in reference.md |
| Publisher endpoint update authentication | Note §4.4 underspecified; Benson requires re-validation for updates |
| Full requirements.md checkbox pass | Use [requirements.md](../.cursor/skills/ivoa-registry-of-registries/requirements.md) for PR reviews; update this file when behaviour changes |

---

## Related

- [production-oai.md](production-oai.md) — deploy and verify `baseURL`
- [implementation-todo.md](implementation-todo.md) — remaining backlog
- [requirements.md](../.cursor/skills/ivoa-registry-of-registries/requirements.md) — full §1–§9 checklist for agents and reviews
