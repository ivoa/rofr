# Validation stylesheets (XSLT)

Default **`ASSETS_ROOT`**: XSLT 1.0 stylesheets for IVOA registry rules beyond XSD.

| File | Role |
|------|------|
| `checkIVOAOAI.xsl` | IVOA harvest profile tests on OAI GET responses (phase 2) |
| `checkVOResource.xsl` | VOResource constraint tests on harvested records (phase 3) |
| `testsVOResource.xsl` | Shared VOResource rule templates (imported by the check stylesheets) |
| `validationCommon.xsl` | Shared helpers (imported by the check stylesheets) |

Full context: [`docs/schemas-and-validation-assets.md`](../../docs/schemas-and-validation-assets.md).
