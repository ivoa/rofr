# ADR 0006: Reuse legacy XSD/XSLT assets unchanged

## Status

Accepted

## Context

The validator’s correctness is tied to **years of curated assets**: XSD bundles under `assets/schemas/`, XSLT under `assets/validate/`, vocabulary generation inputs, and the standards OAI catalog under `assets/standards/`. These files were maintained for the Java WAR and are referenced throughout the functional contract.

Rewriting validation rules in Python would duplicate the Java/XSLT source of truth and make parity testing far harder.

## Decision

**Keep the bundled asset trees** as the authoritative validation artefacts:

- Python code **orchestrates** HTTP harvest, OAI phases, and when to invoke XSD vs XSLT; it does not reimplement IVOA rule logic in Python except where unavoidable (e.g. OAI-PMH server behaviour for Benson’s own `/oai` endpoint).
- Namespace-to-schema mapping lives in code (`benson.xml.catalog`) but points at the same on-disk XSD layout documented in [schemas-and-validation-assets.md](../schemas-and-validation-assets.md).
- Optional tooling (e.g. `benson generate-vocabulary-xsl`) regenerates derived stylesheets when vocabulary sources change.

## Consequences

- **Positive:** Parity tests can diff XML/HTML results against legacy sample bodies; XSLT edits remain portable between stacks.
- **Positive:** IVOA schema updates are still “drop in bundles under `assets/schemas/`” with documented bundle composition.
- **Negative:** Asset weight and XSLT 1.0 constraints remain part of the deployment (mounted `assets/` in dev reload and Docker).
- **Neutral:** Standalone VOR validation always uses the bundled catalog, independent of the harvest `builtinSchemas` flag (see project README).
