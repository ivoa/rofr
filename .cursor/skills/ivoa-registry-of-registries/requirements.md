# Registry of Registries — requirements checklist

Working checklist for implementing or verifying Benson as an IVOA RofR. Mark items when **implemented**, **tested**, and **documented** (use your PR or issue template, or annotate inline).

**Legend:** `MUST` = RI or OAI mandatory · `SHOULD` = RI/OAI/RofR recommended · `NOTE` = RofR Note practice · `LOCAL` = Benson parity only (not IVOA normative)

**Specs:** [RofR Note](https://www.ivoa.net/documents/Notes/RegistryOfRegistries/RegistryOfRegistries-1.0-20070628.html) · [RI 1.1](https://www.ivoa.net/documents/RegistryInterface/) · [OAI-PMH 2.0](https://www.openarchives.org/OAI/openarchivesprotocol.html)

Narrative background: [reference.md](reference.md)

---

## 1. Service role and scope

- [ ] RofR acts as a **publishing registry** (not an end-user search registry). `NOTE` §1; `RI` §4.1
- [ ] Primary clients are **harvesters** (full/searchable registries), not VO search apps. `NOTE` §1
- [ ] **Do not** claim RofR is a master registry or mandatory high-availability service. `NOTE` §3.1
- [ ] **Out of scope** documented if built anyway: end-user publisher picker, searchable-registry bootstrap, SOAP harvest. `NOTE` §4.2–4.3; `RI` §2.1

---

## 2. OAI-PMH repository (RofR as data provider)

### Transport and envelope

- [ ] Supports HTTP **GET** and **POST** for all requests. `MUST` OAI §3.1
- [ ] Single **baseURL**; value in `Identify` matches live endpoint. `MUST` OAI §4.2; `RI` §2.5
- [ ] Responses are well-formed **OAI-PMH 2.0** XML (`responseDate`, `request`). `MUST` OAI §3.2
- [ ] Errors use OAI `error` element with standard **codes** only (no invented codes). `MUST` OAI §3.6
- [ ] `badArgument` when `from` > `until`. `MUST` OAI §2.7.1

### Six verbs

- [ ] **Identify** — complete OAI mandatory fields + RI extensions. `MUST` OAI §4.2; `RI` §2.5
- [ ] **ListMetadataFormats** — lists supported prefixes. `MUST` OAI §4.4
- [ ] **ListSets** — lists repository sets. `MUST` OAI §4.6 (when sets supported)
- [ ] **ListIdentifiers** — headers + date/set filters. `MUST` OAI §4.3
- [ ] **ListRecords** — full records + date/set filters. `MUST` OAI §4.5
- [ ] **GetRecord** — single record by identifier + `metadataPrefix`. `MUST` OAI §4.1

### Metadata formats

- [ ] **`oai_dc`** supported (OAI baseline). `MUST` OAI §2.5; `RI` §2.2
- [ ] **`ivo_vor`** supported (VOResource in `ri:Resource`). `MUST` `RI` §2.2
- [ ] Each `ivo_vor` record has **`xsi:type`** on `ri:Resource`. `MUST` `RI` §2.2
- [ ] `cannotDisseminateFormat` for unknown `metadataPrefix`. `MUST` OAI §3.6

### Identify (RI profile)

- [ ] `description` contains **`ri:Resource`** with **`xsi:type="vg:Registry"`** (self-description). `MUST` `RI` §2.5
- [ ] **`deletedRecord`** declared (`persistent` or `transient` strongly preferred over `no`). `MUST` OAI §2.5.1; `SHOULD` `RI` §2.5
- [ ] If `transient`, deleted records kept **≥ 6 months**. `MUST` `RI` §2.5

### Sets

- [ ] Set **`ivo_managed`** exists and is advertised in **ListSets**. `MUST` `RI` §2.6
- [ ] Records in `ivo_managed` are **locally published** (authority matches `vg:managedAuthority`). `MUST` `RI` §2.6
- [ ] Headers include **`setSpec`** for set membership on List/Get responses. `MUST` OAI §2.6 (when sets used)
- [ ] Set **`ivo_publishers`** on RofR lists **registered** `vg:Registry` records. `SHOULD` `RI` §4.2; `NOTE` §3
- [ ] No custom set names beginning with **`ivo_`**. `SHOULD` `RI` §2.6

### Required records (publishing registry)

- [ ] One self **`vg:Registry`** record (in Identify + harvestable). `MUST` `RI` §2.4
- [ ] Each **`vg:managedAuthority`** has matching **`vg:Authority`** record in `ivo_managed`. `MUST` `RI` §2.4
- [ ] **`vg:Harvest`** capability with **`vg:OAIHTTP`**, `role="std"`, correct **`accessURL`**. `MUST` `RI` §3.4
- [ ] OAI header **identifier** aligns with **`vr:identifier`** (VO convention). `SHOULD` `RI` §2.3

### Selective harvest and flow control

- [ ] Accept **`from`** / **`until`** at **second** UTC granularity (`…Z`). `MUST` `RI` §2.7
- [ ] Emit **datestamps** at second granularity on headers. `MUST` `RI` §2.7
- [ ] **Resumption tokens** when listing exceeds page size; tokens work until list complete. `MUST` OAI §3.5
- [ ] Invalid token → **`badResumptionToken`**. `MUST` OAI §3.6

### RofR-specific holdings

- [ ] **Standards** as `vstd:Standard` in managed set where curated. `SHOULD` `RI` §4.1; `NOTE` §4.1
- [ ] Registered **publishers** exposed via **`ivo_publishers`** (not as “managed” copies of others’ registry records). `NOTE` §3

---

## 3. Registry discovery (harvester / client behaviour)

Use when implementing or testing a client that consumes RofR (or documenting expected harvester use).

- [ ] Step 1: `ListRecords` `metadataPrefix=ivo_vor` **`set=ivo_publishers`** on RofR OAI. `SHOULD` `RI` §4.2; `NOTE` §3
- [ ] First run: **`from` omitted** for full publisher list. `SHOULD` `RI` §4.2; `NOTE` §3
- [ ] Extract **`accessURL`** from `vg:Harvest` / `vg:OAIHTTP` / `role=std`. `NOTE` §3; `RI` §3.4
- [ ] Step 2: harvest each publisher with **`set=ivo_managed`**. `SHOULD` `RI` §4.2
- [ ] New publisher: **no `from`** on first harvest of that endpoint. `NOTE` §3
- [ ] Incremental runs: use cached **`from`**; refresh cache from **`responseDate`**. `NOTE` §3; `SHOULD` `RI` §4.2
- [ ] **Do not** treat Step-1 publisher records as authoritative metadata store (re-harvest from publisher). `NOTE` §3
- [ ] Periodic **full reharvest** and optional **overlap window** documented if client implements incremental-only. `SHOULD` `RI` §4.2
- [ ] RofR down: harvester may continue with cached endpoints. `NOTE` §3.1

---

## 4. Registration and validation workflow

### Admission policy (RofR Note + RI)

- [ ] Provider submits **HTTP GET** OAI base URL (not OAISOAP). `NOTE` §2; `MUST` `RI` §3.4 (HTTP)
- [ ] **Validation** runs OAI conformance + IVOA profile + VOResource on `ivo_managed` harvest. `NOTE` §2; `RI` §4.1
- [ ] **Zero failures** (per deployment policy) before offering registration. `NOTE` §2
- [ ] Registration requires **explicit user confirmation** after validation. `NOTE` §2
- [ ] Accepted listing stores registry record from **Identify** / self-description. `NOTE` §2
- [ ] **Endpoint change** requires re-validation / re-registration (auth TBD in specs). `NOTE` §2, §4.4

### Validator phases (this repository)

- [ ] **Phase 1** — broad OAI-PMH conformance (explorer / matrix). `LOCAL` [functional contract](../../docs/regvalidate-functional-contract.md) §3
- [ ] **Phase 2** — four fixed GETs + `checkIVOAOAI.xsl`. `LOCAL` §3; aligns with `RI` §2
- [ ] **Phase 3** — ListRecords harvest + XSD + `checkVOResource.xsl`. `LOCAL` §3; `NOTE` §2
- [ ] Standalone VOR upload path (optional records, not full harvest). `LOCAL` §4

### Session / HTTP (Benson parity)

- [ ] Harvest validator **`endpoint`** query param (trailing `?` or `&`). `LOCAL` §2.2
- [ ] Legacy paths or API aliases documented if supported. `LOCAL` §2

---

## 5. Operational endpoints (Benson — document, do not invent)

Check against [README.md](../../README.md) and [functional contract](../../docs/regvalidate-functional-contract.md). Verify each exposed route matches documented method, parameters, and response type.

- [ ] RofR OAI publisher (e.g. `GET /oai`). `LOCAL`
- [ ] Publishers OAI XML (`GET /oai`, `set=ivo_publishers`). `LOCAL`
- [ ] Publishers JSON API if present. `LOCAL`
- [ ] Harvest validation UI/API. `LOCAL`
- [ ] Registration update after successful validation (policy env vars). `LOCAL`
- [ ] Publisher **liveness** check command if operated. `LOCAL`

---

## 6. Validation and error handling

- [ ] OAI errors do not leak stack traces unless explicit debug flag. `LOCAL` best practice
- [ ] Registration rejects when Identify identifier **≠** stored IVO identifier. `LOCAL` README (hijack prevention)
- [ ] Unknown OAI verb → **`badVerb`**. `MUST` OAI §3.6
- [ ] Missing record → **`idDoesNotExist`**. `MUST` OAI §3.6
- [ ] Empty list → **`noRecordsMatch`** or valid empty list (per verb rules). `MUST` OAI §4.x

---

## 7. Documentation deliverables

For each **new or changed** public behaviour:

- [ ] Endpoint table: method, path, parameters, content types
- [ ] Example **curl** or HTTP GET URL for OAI
- [ ] Tag each behaviour: **MUST** / **SHOULD** / **NOTE** / **LOCAL**
- [ ] Link to spec section used for the decision
- [ ] Document known **ambiguities** (e.g. `ivo_publishers` not in RI §2.6). See [reference.md](reference.md)

Update project [docs/README.md](../../docs/README.md) when adding operator-facing behaviour.

---

## 8. Tests and evidence

Do not claim compliance without corresponding tests or recorded manual evidence.

| Requirement area | Suggested evidence |
|------------------|-------------------|
| OAI verbs | Automated tests on `/oai` |
| Identify + embedded Registry | XML assertion tests |
| `ivo_managed` / `ivo_publishers` | ListRecords set filters |
| Metadata formats | ListMetadataFormats |
| Resumption | Multi-page ListRecords test |
| `from` / `until` | Incremental harvest tests |
| Validator phases | `pytest` + [docs/samples/](../../docs/samples/) |
| Registration | Integration test for happy path + rejection cases |

- [ ] Test suite covers every **MUST** in sections 2–4 that this deployment implements
- [ ] Parity samples updated or CAPTURE notes if HTTP bodies change. `LOCAL`
- [ ] PR description cites **RI § / OAI § / Note §** for spec-driven changes

---

## 9. Pre-merge review (agent or human)

- [ ] No invented OAI parameters, sets, or error codes
- [ ] Normativity labeled correctly in docs
- [ ] Conflicts between Note and RI **called out**, not silently merged
- [ ] Scope matches request (minimal change; no unrelated refactors)

---

## Quick trace: validator “four GETs”

| # | Query fragment | Satisfies |
|---|----------------|-----------|
| 1 | `verb=Identify` | RI §2.5 |
| 2 | `verb=ListMetadataFormats` | RI §2.2 |
| 3 | `verb=ListSets` | RI §2.6 |
| 4 | `verb=ListRecords&metadataPrefix=ivo_vor&set=ivo_managed` | RI §2.6 |

## Quick trace: ecosystem harvest

| Step | Request | Satisfies |
|------|---------|-----------|
| A | RofR `ListRecords` + `ivo_publishers` | RI §4.2, Note §3 |
| B | Publisher `ListRecords` + `ivo_managed` | RI §4.2, Note §3 |
