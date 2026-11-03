# ADR 0004: lxml for XSD and XSLT 1.0 validation

## Status

Accepted

## Context

Validation depends on **W3C XML Schema** checks against a large offline catalog under `assets/schemas/` and **XSLT 1.0** business rules under `assets/validate/` (same stylesheets the Java `XSLEvaluator` path used). Parsers must resolve local imports without network fetches, support legacy XSLT 1.0, and handle typical IVOA VOResource and OAI-PMH document sizes.

Pure-Python XML libraries vary in XSD completeness and XSLT support; calling external `xmllint`/`xsltproc` per request would complicate deployment and error reporting.

## Decision

Use **`lxml`** (libxml2 + libxslt) for:

- Parsing and holding validation result trees (`lxml.etree`) in harvest run state.
- XSD validation (`benson.xml.xsd_validate`, catalog resolver under `benson.xml.schema_resolver`).
- XSLT 1.0 evaluation (`benson.xml.xslt_eval`) with bundled stylesheets and legacy-compatible timestamp parameters.

System packages **`libxml2`** and **`libxslt1.1`** are documented for Debian/Ubuntu Docker and dev hosts when wheels are insufficient.

## Consequences

- **Positive:** Matches the legacy stack’s reliance on industrial-grade XSD/XSLT engines; one dependency covers parse, schema, and transform.
- **Positive:** Local schema resolution aligns with [schemas-and-validation-assets.md](../schemas-and-validation-assets.md) bundle design.
- **Negative:** Native library dependency in containers and CI (slim images must install runtime libs).
- **Negative:** XSLT 2.0+ is out of scope; assets remain XSLT 1.0 as authored for the Java deployment.
