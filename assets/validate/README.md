# Validation stylesheets (XSLT)

Default **`ASSETS_ROOT`**: XSLT 1.0 stylesheets for IVOA registry rules beyond XSD.

| File | Role |
|------|------|
| `checkIVOAOAI.xsl` | IVOA harvest profile tests on OAI GET responses (phase 2) |
| `checkVOResource.xsl` | VOResource constraint tests on harvested records (phase 3) |
| `testsVOResource.xsl` | Shared VOResource rule templates (imported by the check stylesheets) |
| `validationCommon.xsl` | Shared helpers (imported by the check stylesheets) |
| `validateVocabularies.xsl` | Generated vocabulary-term checks (imported by `checkVOResource.xsl`) |
| `vocabularyControlled.csv` | Config for which VOResource paths are vocabulary-controlled |

## Regenerating vocabulary XSLT

IVOA vocabularies change at most a few times a year. When they do (or when `vocabularyControlled.csv` changes), regenerate the committed stylesheet and commit the result:

```bash
benson generate-vocabulary-xsl
```

This fetches the vocabularies listed in `vocabularyControlled.csv` from `http://www.ivoa.net/rdf/` and overwrites `validateVocabularies.xsl`. Do not edit that XSLT by hand.

Full context: [`docs/schemas-and-validation-assets.md`](../../docs/schemas-and-validation-assets.md).
