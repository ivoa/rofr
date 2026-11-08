# Validation stylesheets (XSLT)

Default **`ASSETS_ROOT`**: XSLT 1.0 stylesheets for IVOA registry rules beyond XSD.
These files are required for validation; a missing or unloadable stylesheet fails hard
(see [`docs/schemas-and-validation-assets.md`](../../docs/schemas-and-validation-assets.md)).

| File | Role |
|------|------|
| `checkIVOAOAI.xsl` | IVOA harvest profile tests on OAI GET responses (phase 2) |
| `checkVOResource.xsl` | VOResource constraint tests on harvested records (phase 3) |
| `testsVOResource.xsl` | Shared VOResource rule templates (imported by the check stylesheets) |
| `validationCommon.xsl` | Shared helpers (imported by the check stylesheets) |
| `validateVocabularies.xsl` | Generated vocabulary-term checks (imported by `checkVOResource.xsl`) |
| `vocabularyControlled.csv` | Config for which VOResource paths are vocabulary-controlled |

## Vocabulary validation — operator flow

Harvest validation embeds the current IVOA term lists in **`validateVocabularies.xsl`**. That file is **generated output** (cached in the repo for offline / standalone validation). Operators do **not** download or hand-edit that stylesheet; the generator writes it.

| You maintain | Role |
|--------------|------|
| `vocabularyControlled.csv` | Which VOResource paths are checked, which RDF vocabulary each uses, mandatory vs warning |
| `validateVocabularies.xsl` | **Output** of `benson generate-vocabulary-xsl` — term lists and XSLT fragments (do not edit by hand) |
| Other `*.xsl` here | Static rule stylesheets (`checkVOResource.xsl` imports the generated file); change only when validation *rules* change, not when vocabulary *terms* change |

`benson generate-vocabulary-xsl` reads `vocabularyControlled.csv`, fetches each listed vocabulary from `http://www.ivoa.net/rdf/` (Desise JSON), and overwrites `validateVocabularies.xsl`. Implementation: [`src/benson/oai/vocabulary_xslt.py`](../../src/benson/oai/vocabulary_xslt.py).

### When IVOA publishes new or changed terms

No repo config change is required unless a new vocabulary URL or field must be checked.

1. From the project root (with network access to `ivoa.net`):

   ```bash
   benson generate-vocabulary-xsl
   ```

2. Review the diff to `validateVocabularies.xsl`.
3. Commit the updated stylesheet and deploy.

### When which fields or vocabularies are validated must change

Follow registry / IVOA guidance (e.g. new controlled attribute, different vocabulary IRI).

1. Edit `vocabularyControlled.csv` (xpath, attribute path, vocabulary path under `ivoa.net/rdf/`, mandatory flag).
2. Run `benson generate-vocabulary-xsl` as above.
3. Commit `vocabularyControlled.csv` and `validateVocabularies.xsl`.

If `validateVocabularies.xsl` is missing, phase-3 validation fails until step 2 is done.

Full context: [`docs/schemas-and-validation-assets.md`](../../docs/schemas-and-validation-assets.md).
