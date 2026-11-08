# Architecture decision records (ADRs)

This folder records **why** Benson (Project Benson / Registry of Registries validator) is built the way it is. Behavioural specs live in [../regvalidate-functional-contract.md](../regvalidate-functional-contract.md); asset layout in [../schemas-and-validation-assets.md](../schemas-and-validation-assets.md).

ADRs use a short [Michael Nygard–style](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions) template:

- **Status** — proposed, accepted, deprecated, superseded
- **Context** — forces and constraints
- **Decision** — what we chose
- **Consequences** — trade-offs and follow-ups

## Index

| ADR | Title | Status |
|-----|--------|--------|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | Accepted |
| [0002](0002-python-service-replaces-java-war.md) | Python service replaces the legacy Java WAR | Accepted |
| [0003](0003-fastapi-starlette-uvicorn.md) | FastAPI, Starlette, and uvicorn for HTTP | Accepted |
| [0004](0004-lxml-for-xsd-and-xslt.md) | lxml for XSD and XSLT 1.0 validation | Accepted |
| [0005](0005-parity-driven-behaviour-contract.md) | Parity-driven behaviour contract | Accepted |
| [0006](0006-reuse-legacy-validation-assets.md) | Reuse legacy XSD/XSLT assets unchanged | Accepted |
| [0007](0007-in-memory-harvest-run-store.md) | In-memory harvest run and session state | Accepted |
| [0008](0008-standards-oai-tombstones.md) | OAI tombstones for withdrawn `ivo_managed` standards | Accepted |

## Adding a new ADR

1. Copy the next number (`0009-…`).
2. Set **Status** to `Proposed` until reviewed, then `Accepted`.
3. Link the ADR from this index.
4. If an ADR is replaced, mark the old one **Superseded by** the new number.
