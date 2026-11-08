# OAI-PMH endpoints — status

Track Benson as a **RofR OAI-PMH data provider** ([Registry Interfaces](https://www.ivoa.net/documents/RegistryInterface/) §2–§4, [RofR Note](https://www.ivoa.net/documents/Notes/RegistryOfRegistries/RegistryOfRegistries-1.0-20070628.html) §3, [OAI-PMH 2.0](https://www.openarchives.org/OAI/openarchivesprotocol.html)).

**Checklist:** [`.cursor/skills/ivoa-registry-of-registries/requirements.md`](../.cursor/skills/ivoa-registry-of-registries/requirements.md)

**Code:** `src/benson/oai/server.py`, `src/benson/http/oai.py`, `src/benson/registry/publisher_oai.py`, `src/benson/http/catalog.py` (`/list-publishers`).

---

## Implemented

| Area | Notes |
|------|--------|
| **`GET` / `POST` `/oai`** | Six verbs, `text/xml`, resumption, `from`/`until`, standard error codes |
| **`ivo_managed`** | RofR self-description, authorities, IVOA standards from `assets/standards/` |
| **`ivo_publishers`** | Registered `vg:Registry` rows from `publishers.json` |
| **`GET /list-publishers`** | Full OAI envelope; same rows as `ListRecords` + `set=ivo_publishers` |
| **Publisher metadata** | `identifier`, `title`, `vg:Harvest` / `vg:OAIHTTP` `role="std"`, `accessURL` |
| **Tests** | `test_standards_oai.py`, `test_registry.py` (sets, POST, resumption, publishers) |

### Harvest URLs

```bash
# RofR infrastructure + standards
curl -sS 'http://localhost:8000/oai?verb=ListRecords&metadataPrefix=ivo_vor&set=ivo_managed'

# Registered publishing registries (Note §3 step 1)
curl -sS 'http://localhost:8000/oai?verb=ListRecords&metadataPrefix=ivo_vor&set=ivo_publishers'

# Legacy alias
curl -sS 'http://localhost:8000/list-publishers'
```

Then harvest each publisher’s `accessURL` with `set=ivo_managed`.

---

## Optional / follow-up

- [ ] **Persist full Identify `description` XML** at registration (richer than title + endpoint today).
- [ ] **`/list-publishers` verb dispatch** — only `ListRecords` is supported on that path; all verbs remain on `/oai`.
- [ ] **Deleted / withdrawn publishers** — tombstone headers when a listing is removed.
- [ ] **`GET /list-searchables`** — still 501; RegTAP/home page covers searchables today.
- [ ] **Parity sample** for `/list-publishers` under `docs/samples/` if production bodies are recaptured.
- [ ] Check off items in `requirements.md` §2–§8 when you want a formal compliance audit.
