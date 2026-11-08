# Parity notes for re-implementing `regvalidate`

Use with [regvalidate-functional-contract.md](regvalidate-functional-contract.md) (behaviour) and [samples/](samples/) (response shapes).

## Why parity

**Parity** here means Benson’s harvest validator and legacy-compatible HTTP API **behave like `http://rofr.ivoa.net` and the Java WAR**—not a separate goal of matching every IVOA document in isolation. The purpose is an **easier transition**: operators, registry providers, and existing scripts can switch to Benson without surprise changes to URLs, session/`op` flows, result XML, status encoding, and phase limits.

- **During rollout:** parity reduces retraining and broken integrations; treat unexpected differences versus production or [samples/](samples/) as bugs unless [compliance.md](compliance.md) or this file records an intentional change.
- **After Benson is the reference deployment:** parity matters most where legacy behaviour was still correct for users; IVOA normative OAI and registration policy are tracked in [compliance.md](compliance.md), not in this file.
- **Closing gaps:** fix or document one area at a time (see sections below). No standing “parity umbrella” backlog item—pick a section, ship a small PR, update fixtures or notes.

## Discovery model

Lack of standalone documentation elsewhere means **`http://rofr.ivoa.net`** plus **this repository** are the practical truth for corner cases—session handling, OAI Explorer quirks, validator result XML shape, lax JSON encoding, HTTP error pages. Automated parity checks (fixture diff, contract tests hitting production or a faithfully deployed Legacy WAR, and behavioural tests anchored to Java/XSLT where needed) guard against undocumented drift during a rewrite.

## OAI phase 3 (harvest iterators)

The contract describes **what** happens (consume ListRecords-oriented OAI output, validate each VOResource). Exact **resumption-token** paging, timeouts, and record caps mirror the legacy Java iterators (`Harvester`, `HarvestRecordServer`, etc.)—not spelled out independently in **`docs/`**. For bit-for-bit parity, diff against archived responses or reuse the **`docs/samples`** capture after a successful full run against your target registry.

## Synchronous versus background record limits

Legacy behaviour uses **`maxVORInclude = 5`** when returning a **synchronous** combined `Validate` result, but **`maxVORInclude = 1`** inside the **`cache=true`** pipeline. Surface this distinction if your API merges those paths.

## Result XML

There is no published XSD for **`OAIValidation`**, **`HarvestValidation`**, or merged **`RegistryValidation`** result wrappers in **`docs/schemas/`**. Those schemas target **protocol and VOResource payloads**, not the validator’s reporting XML. Base tests on element names / attributes illustrated in **`docs/samples`** and **`regvalidate-functional-contract.md` §8.

## Strict JSON

`StartSession` / `GetStatus` bodies historically look like JSON but use **single-quoted strings**. Normalise for strict parsers or snapshot-test at the lexical level described in **`docs/samples/harvest-validater/README.md`**.

## HTTP 500 paths

Synchronised **`op=Validate`** and some follow-on calls against **`http://rofr.ivoa.net`** have returned Tomcat HTML **500** with **`OAI-PMH badVerb`**. Treat as deployment/Explorer sensitivity; fixture: **`docs/samples/harvest-validater/optional-tomcat-500-validate-badverb.html`**.

## OAI Explorer dependence (phase 1)

Replacing **`comply` / OAI Explorer** requires either bundling equivalent requests or dropping phase 1 and documenting the reduced coverage.
