# OAI-PMH endpoints — remaining work

Track what Benson still needs to be a **complete RofR OAI-PMH data provider** (per [Registry Interfaces](https://www.ivoa.net/documents/RegistryInterface/) §2–§4, [RofR Note](https://www.ivoa.net/documents/Notes/RegistryOfRegistries/RegistryOfRegistries-1.0-20070628.html) §3, and [OAI-PMH 2.0](https://www.openarchives.org/OAI/openarchivesprotocol.html)).

**Normative checklist (all sections):** [`.cursor/skills/ivoa-registry-of-registries/requirements.md`](../.cursor/skills/ivoa-registry-of-registries/requirements.md)

**Implementation map:** `src/benson/oai/server.py` (`GET /oai`), `src/benson/http/oai.py`, `src/benson/registry/oai_emit.py` (`GET /list-publishers`).

---

## What already works

These items are implemented and covered by tests (primarily `tests/test_standards_oai.py`):

| Area | Status |
|------|--------|
| **`GET /oai`** — OAI-PMH 2.0 envelope (`responseDate`, `request`, standard error codes) | Done |
| **Six verbs** on `/oai` — Identify, ListMetadataFormats, ListSets, ListIdentifiers, ListRecords, GetRecord | Done |
| **Metadata formats** — `ivo_vor`, `oai_dc`; `cannotDisseminateFormat` for unknown prefixes | Done |
| **Set `ivo_managed`** — ListSets, ListRecords/ListIdentifiers filtering, `setSpec` on headers when `set=ivo_managed` | Done |
| **Identify (RI profile)** — embedded `ri:Resource` `xsi:type="vg:Registry"`, `deletedRecord=persistent`, second-level UTC granularity | Done |
| **Managed holdings** — self `vg:Registry`, `vg:Authority`, IVOA organisation, curated `vstd:Standard` files under `assets/standards/` | Done |
| **Selective harvest** — `from` / `until`, `badArgument` when `from` > `until` | Done |
| **Resumption tokens** — pagination via `OAI_MAX_RECORDS`; invalid token → `badResumptionToken` (phase-1 matrix) | Done (happy-path pagination not yet asserted in tests) |
| **`vg:Harvest` / `vg:OAIHTTP`** on self-description — `role="std"`, `accessURL` = live `/oai` base | Done |
| **Harvest validator client** — phases 1–3 against *foreign* registries (`src/benson/oai/phase*.py`) | Done |

---

## 1. Canonical RofR discovery: `set=ivo_publishers` on `/oai`

**Priority: high.** This is the harvest recipe in RI §4.2 and the RofR Note §3.

- [ ] **`ListSets`** on `/oai` must advertise set **`ivo_publishers`** (in addition to `ivo_managed`), with a sensible `setName` / description.
- [ ] **`ListRecords` / `ListIdentifiers`** with `metadataPrefix=ivo_vor&set=ivo_publishers` must return **registered publishing registries** (`vg:Registry` records), not the standards/authority mix served under `ivo_managed`.
- [ ] **Decide architecture** (document in an ADR if non-obvious):
  - **Option A (spec-aligned):** fold publisher records into `StandardsStore` / `dispatch_oai_verb` on `/oai` (single canonical base URL, matching `http://rofr.ivoa.net/oai`).
  - **Option B (current split):** keep `GET /list-publishers` but also mirror the same records through `/oai?…&set=ivo_publishers` so standard harvesters need only one OAI base URL.
- [ ] **Do not** duplicate other registries’ full metadata in `ivo_managed` (Note §3); publisher listings belong under `ivo_publishers` only.
- [ ] **Document** the ambiguity that `ivo_publishers` appears in RI §4.2 / Note §3 but not in RI §2.6’s reserved-set table (see skill `reference.md`).

**Today:** only `ivo_managed` exists on `/oai`; publishers are exposed only at **`GET /list-publishers`**, which is outside the six-verb OAI dispatcher.

---

## 2. `GET /list-publishers` — OAI shape vs OAI-PMH protocol

**Priority: high** if this URL remains a public catalog; **medium** if all traffic moves to `/oai?set=ivo_publishers`.

Either deprecate this path in favour of `/oai`, or bring it to OAI-PMH compliance:

- [ ] Full **`OAI-PMH` envelope** — `responseDate`, `request` (with base URL and parameters), `xsi:schemaLocation` if required for parity.
- [ ] **Verb dispatch** — not only a static `ListRecords` fragment; support at least the same verbs as `/oai` for the publisher list, or return `HTTP 301`/`Link` to the canonical `/oai` queries.
- [ ] **Record headers** — `datestamp` (from `registered_at` / `updated_at`), `setSpec` (`ivo_publishers`), optional `status` for removals.
- [ ] **Rich `vg:Registry` metadata** — harvesters expect records comparable to the publisher’s **Identify** self-description, not title + bare `accessURL` only (`src/benson/registry/oai_emit.py`). Consider persisting the validated Identify `description` payload at registration time (`src/benson/registry/registration.py` currently stores identifier, title, and endpoint only).
- [ ] **`vg:OAIHTTP` `role="std"`** on the harvest interface (matches `registry_self.py` and RI §3.4).
- [ ] **Consistent `standardID`** — align `ivo://ivoa.net/std/Registry` vs `ivo://ivoa.net/std/registry` with RI and with `harvest_access_url_from_metadata` in `rofr_lists.py`.
- [ ] **HTTP POST** if this endpoint stays OAI-PMH (OAI §3.1 **MUST** when claiming full protocol support).

---

## 3. `GET /oai` — protocol gaps

**Priority: medium** (several are OAI **MUST**s).

- [ ] **HTTP POST** for all OAI requests on `/oai` (`src/benson/http/oai.py` is GET-only today). OAI §3.1.
- [ ] **`GetRecord` / List without `set`** — confirm headers include `setSpec` where RI expects set membership (today `setSpec` is omitted on GetRecord and on lists with no `set` argument).
- [ ] **`Content-Type`** — OAI examples use `text/xml`; Benson serves `application/xml`. Confirm parity with `rofr.ivoa.net` and harvest tools; change if legacy expects `text/xml`.
- [ ] **`baseURL` in Identify** — verify behind reverse proxies (`BENSON_PROXY_HEADERS`, `url_for`) matches the URL harvesters use in production.
- [ ] **Deleted / withdrawn standards** — `deletedRecord=persistent` is declared; define behaviour when a standard file is removed or marked deleted (tombstone headers, datestamps).
- [ ] **Transient deletions** — if ever using `transient`, RI §2.5 requires keeping deleted records ≥ 6 months.

---

## 4. Related catalog endpoints (out of OAI-PMH core, RofR Note)

**Priority: low** unless operators require parity with historical RofR HTML lists.

- [ ] **`GET /list-searchables`** — currently **501** stub (`src/benson/http/catalog.py`). Note §4.3 discusses searchable registries; home page + RegTAP cache may suffice; document scope if intentionally omitted.
- [ ] **Publisher discovery for the UI** — `load_publishers` may read JSON or `/list-publishers` OAI XML; keep in sync when OAI publisher layout changes.

---

## 5. Tests and evidence

**Priority: medium** — required before claiming full RofR OAI compliance.

| Gap | Suggested test |
|-----|----------------|
| `ivo_publishers` on `/oai` | `ListRecords` + `ListSets`; assert only registered `vg:Registry` rows |
| Publisher registration → OAI | Register fixture publisher; harvest via `set=ivo_publishers`; XSD + `checkVOResource.xsl` on metadata |
| **Resumption happy path** | Set `OAI_MAX_RECORDS=2`, walk tokens until list complete |
| **POST /oai** | Mirror phase-1 Identify / ListRecords cases with `POST` body |
| **`oai_dc` dissemination** | GetRecord + ListRecords spot checks |
| **`from` / `until`** on `/oai` | Incremental harvest slice tests |
| **`/list-publishers`** | Envelope XSD (`validate_oai_response_envelope`) or parity sample under `docs/samples/` |
| **Self-harvest** | Run phase 2 four GETs against Benson’s own `/oai` in CI (already partially covered by `test_phase2_ivoa_gets`) |

Update parity fixtures in `docs/samples/` when response bodies change.

---

## 6. Documentation deliverables

- [ ] **`docs/README.md` / root `README.md`** — once `ivo_publishers` exists, document the **two-set model** (`ivo_managed` = infrastructure + standards, `ivo_publishers` = registered publishing registries) and example harvest URLs.
- [ ] **Example `curl` commands** for each verb and for the Note §3 two-step harvest (RofR `ivo_publishers`, then each publisher `ivo_managed`).
- [ ] **Deployment note** — canonical OAI base (`/oai` only vs `/list-publishers` legacy path).
- [ ] Mark completed rows in [requirements.md](../.cursor/skills/ivoa-registry-of-registries/requirements.md) §2 and §8 when implemented.

---

## Quick reference — Benson OAI URLs today

| URL | Role | OAI-PMH verbs? |
|-----|------|----------------|
| `GET /oai` | Standards + RofR self/authority records (`set=ivo_managed`) | Yes (GET only) |
| `GET /list-publishers` | Registered publishers (static ListRecords XML) | No |
| *Target registries* (`endpoint` in validator) | Foreign publishing registries under test | Validated by harvest phases 1–3 |

**Ecosystem harvest (not yet fully supported on Benson’s own host):**

1. `GET /oai?verb=ListRecords&metadataPrefix=ivo_vor&set=ivo_publishers` → list of publishing registries  
2. For each `accessURL`, `GET …?verb=ListRecords&metadataPrefix=ivo_vor&set=ivo_managed`

Step 1 today must use `/list-publishers` as a non-standard workaround until §1 above is complete.
