# ADR 0002: Python service replaces the legacy Java WAR

## Status

Accepted

## Context

The Registry of Registries validator historically shipped as an **Ant/Ivy/Tomcat WAR** with servlet entry points (`HarvestValidater`, `VOResourceValidater`) and shared Java validation helpers. That stack is hard to deploy on modern infrastructure, and the team wanted a **maintained** implementation that keeps the same HTTP semantics, XSD/XSLT pipeline, and parity with `http://rofr.ivoa.net`.

The functional contract explicitly treats the Java code as optional reference material: a rewrite needs equivalents for HTTP, XML parsing, XSD, XSLT 1.0, and OAI Explorer invocation—not servlet APIs.

## Decision

Implement **Benson** as a **Python 3.13+** package (`src/benson/`) with:

- A single process that serves the web UI, REST-style harvest API, OAI catalog endpoints, and CLI subcommands (`benson`, `benson check-publishers`, and others).
- The legacy Java tree retained in-repo **for posterity and parity archaeology** only ([regvalidate-legacy-java-deployment.md](../regvalidate-legacy-java-deployment.md)).

## Consequences

- **Positive:** Simpler container story (see Dockerfile), familiar tooling (`pytest`, `pip install -e ".[dev]"`), and one language for HTTP + validation orchestration.
- **Positive:** Behaviour remains specified in [regvalidate-functional-contract.md](../regvalidate-functional-contract.md), independent of language.
- **Negative:** Phase 1 OAI Explorer integration may still depend on external `comply` or remote explorer URLs, same as the legacy deployment.
- **Negative:** Contributors must compare against Java-era samples and live production when behaviour is ambiguous ([regvalidate-parity-notes.md](../regvalidate-parity-notes.md)).
