# ADR 0001: Record architecture decisions

## Status

Accepted

## Context

Benson replaces a long-running **Java servlet WAR** (`ivoaharvest`, `dalvalidate`) while preserving validator behaviour and bundled IVOA assets. Much of the written material in `docs/` describes **what** the service must do (HTTP operations, validation phases, XSD/XSLT roles), not **which libraries and runtime** implement it.

Contributors and deployers need a durable place for stack choices (FastAPI, lxml, parity strategy, and similar) without mixing them into the normative functional contract.

## Decision

We maintain **architecture decision records** under `docs/adr/`. Each ADR is one numbered markdown file with context, decision, and consequences. The [README](README.md) index lists all ADRs and the process for adding new ones.

## Consequences

- **Positive:** Technical rationale is discoverable next to behavioural docs; future changes can supersede an ADR explicitly.
- **Negative:** ADRs can drift from code if not updated when the stack changes; authors should amend or supersede ADRs when making major technical shifts.
- **Neutral:** ADRs are not a substitute for [regvalidate-functional-contract.md](../regvalidate-functional-contract.md) or parity fixtures under [../samples/](../samples/).
