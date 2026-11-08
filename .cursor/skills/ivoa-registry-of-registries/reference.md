# IVOA Registry of Registries — implementation reference

Concise map of spec obligations for a RI-compliant **publishing** RofR. Cite section numbers in design notes and tests.

**Working checklist:** [requirements.md](requirements.md)

## Required functionality

### Role of the RofR (combined specs)

| Capability | Normativity | Spec |
|------------|-------------|------|
| RI-compliant **publishing registry** exposing OAI-PMH | MUST (RofR as registry) | RI §4.1; RofR Note §1 |
| Catalogue of **registered publishing registries** (`vg:Registry`) | Operational goal | RI §4.1–4.2; RofR Note §2–3 |
| **Validator** before acceptance into catalogue | Note practice | RofR Note §2; RI §4.1 (validator package) |
| **IVOA standards** records (`vstd:Standard`) in RofR holdings | Recommended / curated | RI §4.1; RofR Note §4.1 |
| End-user **search** or master-registry semantics | Out of scope | RofR Note §1, §4.2–4.3 |
| High availability | Weak requirement | RofR Note §3.1 |

Clients of the RofR are **other registries** (harvesters), not general VO search applications.

## Endpoints and operations

### OAI-PMH (normative core)

- **Transport:** HTTP `GET` or `POST`; repository MUST support both (OAI §3.1).
- **Base URL:** Single base; exposed as `baseURL` in `Identify` (OAI §4.2; RI §2.5).
- **Verbs:** `Identify`, `ListMetadataFormats`, `ListSets`, `ListIdentifiers`, `ListRecords`, `GetRecord` (OAI §4).

**RI profile checks** (validator “four GETs” and harvest conformance):

| Step | Request | RI / OAI |
|------|---------|----------|
| 1 | `verb=Identify` | RI §2.5: `description` contains `ri:Resource` `xsi:type="vg:Registry"` |
| 2 | `verb=ListMetadataFormats` | Must include `ivo_vor` and `oai_dc` (RI §2.2) |
| 3 | `verb=ListSets` | Must list `ivo_managed` (RI §2.6) |
| 4 | `verb=ListRecords&metadataPrefix=ivo_vor&set=ivo_managed` | Managed records only (RI §2.6) |

**RofR-specific harvest (discovery):**

| Operation | Parameters | Normativity |
|-----------|------------|-------------|
| `ListRecords` | `metadataPrefix=ivo_vor`, `set=ivo_publishers` | RI §4.2 **recommended**; RofR Note §3 **recipe** |
| `ListRecords` | `set=ivo_managed` on each publisher `accessURL` | RI §4.2 **recommended** |

`ivo_publishers` is the RofR set for registered publishing registries (`vg:Registry`); `ivo_managed` is defined in RI §2.6 for all VO harvestable registries.

**Canonical RofR OAI URL (RI):** `http://rofr.ivoa.net/oai` — implementations may use another host but must document divergence.

### Registration and validation (Note + RI §4.1)

RofR Note §2 (practice):

1. Provider submits publishing registry **OAI HTTP GET** base URL (not SOAP).
2. Background **validation**: all OAI verbs; RI constraints; `ListRecords` with `set=ivo_managed`; VOResource schema + extensions on harvested records.
3. **No failures** required for “fully compliant”; explicit user action to **register**.
4. Stored registry record derived from **Identify** / registry self-description.
5. **Re-registration** when harvest endpoint changes (RofR Note §2, §4.4).

RI §4.1 adds: enrollment via RofR web interface; validator checks OAI and listed resources; only validated registries accepted.

**Not fully specified in IVOA docs:** authentication for endpoint updates (RofR Note §4.4); exact HTTP surface of validator — see project [regvalidate-functional-contract.md](../../docs/regvalidate-functional-contract.md).

### Optional / convenience (not normative IVOA)

- Browser listing of publishers (RofR Note §4.2).
- JSON publishers API, HTML validator UI, async jobs — **Benson deployment** only unless explicitly required.

## Protocol requirements

### OAI-PMH (mandatory behaviours)

- Responses: XML `OAI-PMH` root; errors in `error` element with `code` (OAI §3.2, §3.6).
- **Selective harvest:** `from` / `until` inclusive; `from` ≤ `until` or `badArgument` (OAI §2.7.1).
- **Sets:** optional in OAI; `set` argument on `ListRecords` / `ListIdentifiers` (OAI §2.6–2.7.2).
- **Resumption:** `resumptionToken` when result sets are incomplete (OAI §3.5).
- **Deleted records:** level declared in `Identify` (`no` | `transient` | `persistent`) (OAI §2.5.1; RI §2.5 discourages `no`).
- **Identifiers in headers:** URI syntax; in VO, OAI identifier **should match** `vr:identifier` (RI §2.3).

### Registry Interfaces (IVOA MUST / SHOULD)

| Requirement | Section |
|-------------|---------|
| Publishing registries MUST support harvesting interface | RI §2 intro |
| Searchable registries SHOULD support harvesting | RI §2 intro |
| Metadata: `oai_dc` + `ivo_vor` | RI §2.2 |
| `ri:Resource` with `xsi:type` on VOR records | RI §2.2 |
| Self `vg:Registry` record + `vg:Authority` per managed authority | RI §2.4 |
| `Identify` embeds self `vg:Registry` | RI §2.5 |
| Set `ivo_managed` MUST exist | RI §2.6 |
| Datestamps seconds granularity; accept `from`/`until` with `Z` | RI §2.7 |
| `vg:Harvest` capability with `vg:OAIHTTP` `role="std"` and `accessURL` | RI §3.4 |
| Reserved `ivo_*` set names — do not invent custom `ivo_*` sets | RI §2.6 |

### Incremental harvesting (recommended)

- First harvest: omit `from` (RI §4.2; RofR Note §3).
- Later: use `from` from cached last successful harvest; update cache from `responseDate` (RofR Note §3).
- Overlap window and periodic full reharvest (RI §4.2 **recommended**).
- New publisher: full harvest without `from` on first visit to that endpoint (RofR Note §3).

### Pagination and timestamps

- Honour `resumptionToken` until list complete (OAI §3.5).
- Use server `responseDate` for client clock alignment (RofR Note §3).
- VO registries: second-level UTC datestamps (RI §2.7).

## XML and metadata requirements

- **Envelope:** OAI 2.0 namespace `http://www.openarchives.org/OAI/2.0/`.
- **Payload:** `ivo_vor` → `ri:Resource` (Registry Interface schema) with appropriate `xsi:type` (`vg:Registry`, `vg:Authority`, `vstd:Standard`, services, etc.).
- **Publisher discovery field:** harvest endpoint at  
  `capability[@xsi:type='vg:Harvest']/interface[@xsi:type='vg:OAIHTTP' and @role='std']/accessURL`  
  (RofR Note §3; RI §3.4).
- **Validation assets:** VOResource, Registry Interface, VORegistry, VOStandard schemas; local catalog in [assets/schemas/](../../assets/schemas/) and [schemas-and-validation-assets.md](../../docs/schemas-and-validation-assets.md).

## Validation and error handling

### OAI error codes (use as defined — do not invent)

`badArgument`, `badResumptionToken`, `badVerb`, `cannotDisseminateFormat`, `idDoesNotExist`, `noRecordsMatch`, `noSetHierarchy`, `noMetadataFormats` (OAI §3.6).

### Registry admission validation (RofR)

- Phase A: OAI-PMH conformance (broad request matrix).
- Phase B: Four fixed GETs + IVOA XSLT rules (`checkIVOAOAI.xsl` in this repo).
- Phase C: Harvest `ivo_managed` records; XSD + `checkVOResource.xsl`.

Failures block registration when policy requires zero failures (RofR Note §2). Warnings and recommendations are distinct from failures.

### Registration policy (implementation-defined constants)

Benson uses env vars such as `REGISTRATION_MAX_FAILURES` — document in README, not in IVOA specs.

## Documentation expectations

For each public endpoint document:

- HTTP method and path
- Query/body parameters
- Response content types (`text/xml` for OAI)
- Example request URL (OAI GET)
- Whether behaviour is **RI MUST**, **RI SHOULD**, **RofR Note**, or **local parity**

Update [README.md](../../README.md) for operators and [docs/README.md](../../docs/README.md) for spec links.

## Tests and evidence

| Area | Minimum evidence |
|------|------------------|
| OAI verbs | Happy path + representative error (`badVerb`, `badArgument`) |
| `Identify` | Embedded `vg:Registry`, `deletedRecord`, granularity |
| Sets / formats | `ivo_managed`, `ivo_vor` present |
| RofR lists | `ivo_publishers` vs `ivo_managed` content rules |
| Validator | Golden samples under [docs/samples/](../../docs/samples/) or parity with reference deployment |
| Incremental harvest | `from`/`until` filtering if implemented |

Do not claim “IVOA compliant” without naming which spec and which tests.

## Specification section index

### Registry of Registries Note (2007-06-28)

| § | Topic |
|---|--------|
| Status | Note, not standard |
| 1 | RofR role; not master/end-user registry |
| 2 | Registration + validation workflow |
| 3 | Discovery: `ivo_publishers`, two-step harvest, downtime |
| 4.1 | Standards published via RofR |
| 4.2–4.3 | Browser views, searchable discovery — optional / out of scope |
| 4.4 | Security for endpoint updates — underspecified |

### Registry Interfaces 1.1 (2018-07-23 REC)

| § | Topic |
|---|--------|
| 2.1–2.7 | IVOA OAI constraints |
| 3.1–3.4 | Authority, Registry, Harvest capability |
| 4.1 | RofR description and enrollment |
| 4.2 | Harvesting RofR and publishers |
| 5+ | Search (RegTAP etc.) — not RofR core |

### OAI-PMH 2.0

| § | Topic |
|---|--------|
| 3.1 | HTTP GET/POST |
| 3.5 | Resumption tokens |
| 3.6 | Errors |
| 4.1–4.6 | Verb definitions |

## Known ambiguities (flag, do not silently resolve)

1. **`ivo_publishers` set** — used in RI §4.2 and RofR Note §3; not listed in RI §2.6 reserved sets (only `ivo_managed` defined there). Treat as **RofR implementation requirement** backed by RI harvest recipe.
2. **Validator HTTP API** — RofR Note describes HTML form workflow; exact parameters are defined by deployment ([functional contract](../../docs/regvalidate-functional-contract.md)).
3. **RofR Note vs RI 1.1** — Note references RI 1.01; RI 1.1 is authoritative for protocol MUSTs.
4. **Identify URL trailing `?`/`&`** — legacy validator convention in Benson contract §2.2, not OAI generic.

## This repository (Benson) mapping hints

| Spec concept | Typical Benson location |
|--------------|-------------------------|
| RofR OAI publisher | `GET /oai`, `src/benson/oai/` |
| Publishers catalogue OAI | `GET /oai` (`set=ivo_publishers`) |
| Publishers JSON | `GET /api/v1/registry/publishers` |
| Harvest validation | `/validator`, `/api/v1/registry-validate/harvest` |
| Standards records | `assets/standards/`, `set=ivo_managed` on `/oai` |

Use this table for navigation only; behaviour must still trace to the specs above.
