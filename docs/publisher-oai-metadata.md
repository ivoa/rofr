# Publisher listings and Identify metadata

## RofR Note §2

The [Registry of Registries Note §2](https://www.ivoa.net/documents/Notes/RegistryOfRegistries/RegistryOfRegistries-1.0-20070628.html) says the stored listing should come from the **publisher’s Identify self-description**, not a hand-built stub.

Benson captures the `ri:Resource` `xsi:type="vg:Registry"` from the validated Identify `description` during harvest (phase 2) and stores it in `publishers.json` as **`identify_resource_xml`**. That XML is served in OAI **`set=ivo_publishers`** (`ListRecords` / `GetRecord`, `metadataPrefix=ivo_vor` or `oai_dc`).

If no XML was stored (legacy rows or Identify without an embedded registry), Benson still emits a **minimal** `vg:Registry` built in `publisher_oai.py` (identifier, title, harvest `accessURL`).

## JSON field

| Field | Set when | Used for |
|-------|----------|----------|
| `identify_resource_xml` | Registration or update after a validation run that parsed Identify | OAI publisher metadata body |
| `oai_identifier`, `title`, `harvest_access_url` | Registration form + run endpoint | Indexing, UI, stub fallback, checks |

Re-validation on **update** refreshes `identify_resource_xml` when Identify is parsed again; otherwise the previous XML is kept.

## Before and after (OAI metadata body)

Examples show the `ri:Resource` inside `ListRecords` / `GetRecord` with `set=ivo_publishers` (header and OAI envelope omitted). Same publisher (CADC-style); illustrative URLs.

### Stub fallback (no `identify_resource_xml` in JSON)

Legacy rows or registration without parsed Identify still use a **synthesized** record (~10 lines):

```xml
<ri:Resource xmlns:ri="http://www.ivoa.net/xml/RegistryInterface/v1.0"
             xmlns:vg="http://www.ivoa.net/xml/VORegistry/v1.0"
             xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
             xsi:type="vg:Registry"
             status="active">
  <ri:title>CADC Registry</ri:title>
  <ri:identifier>ivo://cadc.nrc.ca/registry</ri:identifier>
  <ri:capability standardID="ivo://ivoa.net/std/Registry" xsi:type="vg:Harvest">
    <ri:interface xsi:type="vg:OAIHTTP" role="std" version="1.0">
      <ri:accessURL>https://ws.cadc-ccda.hia-iha.nrc-cnrc.gc.ca/reg/oai</ri:accessURL>
    </ri:interface>
  </ri:capability>
</ri:Resource>
```

Enough for harvest discovery (identifier + standard OAI `accessURL`). No curation, content, `managedAuthority`, or other capabilities.

### With stored Identify (after this change)

**`publishers.json`** holds the full `description` payload; OAI serves it verbatim (excerpt from the CADC Identify fixture):

```xml
<ri:Resource xmlns:ri="http://www.ivoa.net/xml/RegistryInterface/v1.0"
             xmlns:vg="http://www.ivoa.net/xml/VORegistry/v1.0"
             xmlns:vr="http://www.ivoa.net/xml/VOResource/v1.0"
             xmlns:vs="http://www.ivoa.net/xml/VODataService/v1.1"
             xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
             xsi:type="vg:Registry"
             status="active"
             created="2011-12-09T14:24:09Z"
             updated="2021-09-19T23:00:20Z">
  <title>CADC Registry</title>
  <shortName>CADC Registry</shortName>
  <identifier>ivo://cadc.nrc.ca/registry</identifier>
  <curation>
    <publisher>Canadian Astronomy Data Centre</publisher>
    <contact>
      <name>John Ouellette</name>
      <email>john.ouellette@nrc-cnrc.gc.ca</email>
    </contact>
  </curation>
  <content>
    <subject>registry</subject>
    <description>CADC Registry</description>
    <referenceURL>https://ws.cadc-ccda.hia-iha.nrc-cnrc.gc.ca/reg</referenceURL>
    <type>Registry</type>
  </content>
  <capability standardID="ivo://ivoa.net/std/Registry" xsi:type="vg:Harvest">
    <interface role="std" xsi:type="vg:OAIHTTP">
      <accessURL>https://ws.cadc-ccda.hia-iha.nrc-cnrc.gc.ca/reg/oai</accessURL>
    </interface>
    <maxRecords>100</maxRecords>
  </capability>
  <full>false</full>
  <managedAuthority>cadc.nrc.ca</managedAuthority>
</ri:Resource>
```

| | Stub | Stored Identify |
|---|------|-----------------|
| Source | `title` + form fields + validation `endpoint` | Identify `description` at registration |
| Aligns with Note §2 | Approximate | Yes |
| `metadataPrefix=oai_dc` | Title + identifier mainly | Richer Dublin Core from full resource |

## Code

- Extract: `extract_identify_registry_resource_xml()` in `src/benson/oai/phase2.py`
- Session: `HarvestRun.identify_resource_xml`
- Persist: `src/benson/registry/registration.py`, `publishers_store.py`
- OAI emit: `publisher_metadata_element()` in `src/benson/registry/publisher_oai.py`
