# ADR 0005: Parity-driven behaviour contract

## Status

Accepted

## Context

External documentation for the Registry of Registries validator has been **sparse**. Production at **`http://rofr.ivoa.net`**, the in-repo Java/XSL implementation, and checked-in **HTTP fixtures** under `docs/samples/` jointly define corner cases: session/`runid` flows, pseudo-JSON status encoding, phase ordering, OAI Explorer quirks, and HTTP 500 paths.

A rewrite that only followed IVOA standards documents would miss deployment-specific behaviour that publishing registries and operators already rely on.

## Decision

Treat **behavioural parity** as a first-class engineering constraint:

1. **Normative prose** for implementers lives in [regvalidate-functional-contract.md](../regvalidate-functional-contract.md) (HTTP surface, three validation phases, `builtinSchemas`, namespace map).
2. **Intentional divergences** and edge cases are recorded in [regvalidate-parity-notes.md](../regvalidate-parity-notes.md).
3. **Automated tests** and **sample captures** (`docs/samples/`) guard against undocumented drift; refresh procedures are documented (e.g. [CAPTURE.md](../samples/harvest-validater/CAPTURE.md)).

Technology choices (Python, FastAPI) must not change observable validator semantics unless an ADR or parity note documents the change.

## Consequences

- **Positive:** Clear priority when prose and production disagree: fix bugs or document intentional change, then update fixtures/tests.
- **Positive:** New contributors have a reading order: contract → assets guide → samples/parity notes ([docs/README.md](../README.md)).
- **Negative:** Some legacy quirks (lax JSON, servlet session URLs) are preserved for compatibility rather than “cleaned up” silently.
- **Neutral:** Benson may add **new** endpoints (e.g. `/validator/jobs`) while keeping legacy-compatible API paths under `/api/v1/registry-validate/`.
