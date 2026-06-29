# Registry validate — documentation index

Documents for validating IVOA registry **OAI-PMH** endpoints (`/regvalidate`) and optional **standalone VOResource** checks.

Historical documentation elsewhere is sparse: treat **parity** with **`http://rofr.ivoa.net`** and the **in-repo implementation** as the main guardrail during a rewrite. See **[`samples/`](samples/)** fixed captures and **[`regvalidate-parity-notes.md`](regvalidate-parity-notes.md)**.

---

## Rewrite or new implementation

Use the **functional contract** (language-neutral HTTP behavior, OAI phases, fixed four IVOA GETs, XSD catalog under `docs/schemas/`, XSLT roles, samples):

[**regvalidate-functional-contract.md**](regvalidate-functional-contract.md)

That file is normative for **what** must be reproduced. Local XML Schema files live in [**schemas/**](schemas/) next to these docs.

**Parity / golden samples:** [**samples/**](samples/) (HTTP bodies + [**CAPTURE.md**](samples/harvest-validater/CAPTURE.md)); edge cases [**regvalidate-parity-notes.md**](regvalidate-parity-notes.md).

---

## Legacy Java WAR / Ant / Tomcat

Use **maintainer** documentation for the existing servlet application (Ivy/Ant **`regvalidate.war`**, **`web.xml`**, `mod_jk`, source class map, CGI registration):

[**regvalidate-legacy-java-deployment.md**](regvalidate-legacy-java-deployment.md)

---

## Quick links

| Topic | Document |
|-------|----------|
| HTTP surface, session / `runid`, `op` catalogue, OAI ladder | [Functional contract §2–3](regvalidate-functional-contract.md#2-http-surface-compatibility) |
| Standalone VOResource (`POST` multipart, Benson curl) | [Project README § Standalone VOResource](../README.md#standalone-voresource-validation), [functional contract §4](regvalidate-functional-contract.md#4-standalone-voresource-validator), [samples](samples/voresource-validater/README.md) |
| `builtinSchemas`, [`docs/schemas`](schemas/) catalog | [Functional contract §2.3](regvalidate-functional-contract.md#23-optional-harvest-parameters), [§5](regvalidate-functional-contract.md#5-namespace-to-schema-file-mapping) |
| Phase 1 OAI Explorer vs Phase 2 four verbs vs Phase 3 VOR | [Functional contract §3](regvalidate-functional-contract.md#3-oai-endpoint-verification-steps) |
| **`docs/samples/`** parity captures + refresh script | [**samples/README.md**](samples/README.md), [**parity notes**](regvalidate-parity-notes.md) |
| Servlet classes, Ant targets, Ivy | [Legacy deployment](regvalidate-legacy-java-deployment.md) |
