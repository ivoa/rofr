# Bundled XML schemas (XSD)

This directory is the default **`SCHEMA_ROOT`**: W3C XML Schema files for offline OAI and IVOA registry validation.

**Developer documentation** (bundles, namespace map, validation flow, related folders):

→ [`docs/schemas-and-validation-assets.md`](../../docs/schemas-and-validation-assets.md)

Quick reference:

| File | Role |
|------|------|
| `benson-oai-bundle.xsd` | Composition root for OAI-PMH envelope checks |
| `benson-ivoa-bundle.xsd` | Composition root for `ri:Resource` + `xsi:type` extensions |
| `*.xsd` | Individual namespace schemas (see doc for full table) |

Namespace URI → filename mapping: [`src/benson/xml/catalog.py`](../../src/benson/xml/catalog.py).

To replace ivoa.net schemas with the current Rec-stage documents those namespace URLs serve:

```bash
benson refresh-schemas
```

Commit the updated files. Non-IVOA schemas (OAI, Dublin Core, W3C) are left alone.
