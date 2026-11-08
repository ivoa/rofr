---
name: ivoa-registry-of-registries
description: Guides Python implementation of IVOA Registry of Registries (RofR) OAI publishing, registration, discovery, and validation against Registry Interfaces, the RofR Note, and OAI-PMH. Use when implementing or changing Benson/RofR endpoints, OAI-PMH responses, publisher registration, standards catalog, harvest validation, or RofR documentation and compliance tests.
---

# IVOA Registry of Registries

## Purpose

This Skill will guide the development of a Python implementation of the IVOA Registry of Registries functionality.

The implementation must provide the functionality, service endpoints, protocol behaviour, and documentation necessary to support the IVOA Registry of Registries model.

## Reference specifications

Use these documents as the primary references:

1. Registry of Registries 1.0 (2007):
   https://www.ivoa.net/documents/Notes/RegistryOfRegistries/RegistryOfRegistries-1.0-20070628.html

2. Registry Interfaces 1.1 (2018):
   https://www.ivoa.net/documents/RegistryInterface/

3. Open Archives Initiative Protocol for Metadata Harvesting (OAI-PMH):
   https://www.openarchives.org/OAI/openarchivesprotocol.html

Pay particular attention to the distinction between normative requirements in the Recommendations and the recommended practices described in the Registry of Registries Note.

## Responsibilities

When implementing functionality using this Skill:

1. Consult the relevant specifications before designing or implementing functionality.
2. Identify required service endpoints, HTTP methods, parameters, response formats, and protocol behaviours.
3. Ensure OAI-PMH operations and XML responses conform to the applicable specifications.
4. Implement appropriate validation and error handling.
5. Ensure the registry supports the necessary resource descriptions, metadata formats, and harvesting operations.
6. Implement the registration and registry discovery workflows described in the Registry of Registries document.
7. Ensure the implementation handles pagination, incremental harvesting, and protocol timestamps correctly where required.
8. Produce documentation describing supported functionality, endpoints, parameters, responses, and examples.
9. Include tests that verify protocol compliance and expected behaviour.

## Accuracy requirements

- Never invent protocol requirements or endpoint behaviour.
- Distinguish mandatory requirements from recommendations and optional capabilities.
- Reference the relevant specification sections when making implementation decisions.
- Where the specifications are ambiguous or conflicting, identify the issue rather than silently choosing an interpretation.
- Do not claim compliance without appropriate tests and evidence.

## Workflow

1. Classify the task (OAI publisher, registration/validation UI or API, harvest client, documentation, tests).
2. Work through [requirements.md](requirements.md) for the relevant sections; use [reference.md](reference.md) for section pointers and normativity (MUST vs should vs Note practice).
3. Open the cited spec sections before writing code.
4. For this repository, treat [docs/regvalidate-functional-contract.md](../../docs/regvalidate-functional-contract.md) and [docs/samples/](../../docs/samples/) as the **deployment parity contract** for Benson; they do not override IVOA Recommendations but may document legacy HTTP paths and quirks.
5. Record decisions in code comments, ADRs, or docs only when non-obvious; cite RI § / OAI § / RofR Note § in PR descriptions when behaviour is spec-driven.
6. Add or extend tests (`tests/test_oai*.py`, `tests/test_standards_oai.py`, harvest fixtures) for any claimed protocol behaviour.

## Normativity ladder

| Source | Status | Role |
|--------|--------|------|
| OAI-PMH 2.0 | External standard | Six verbs, XML envelope, errors, selective harvest, resumption tokens |
| Registry Interfaces 1.1 | IVOA Recommendation | IVOA harvesting constraints, sets, metadata, RofR in §4 |
| Registry of Registries 1.0 | IVOA Note | Registration UX, validator workflow, discovery recipe, out-of-scope features |
| Benson functional contract | Project-local | HTTP compatibility with `rofr.ivoa.net`, session validator, samples |

When the Note and Recommendation disagree, **stop and document**; default implementation authority is **Registry Interfaces** for protocol; **Note** for described RofR operational practice where RI is silent.
