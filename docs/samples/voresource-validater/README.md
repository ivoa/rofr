# Standalone VOResource validation samples

## Benson (current)

**Endpoint:** `POST /api/v1/registry-validate/voresource`  
**Content type:** `multipart/form-data`

| Field | Description |
|-------|-------------|
| `record` | File upload (repeat for multiple files, max **10**) |
| `recordURL` | Space-separated `http`/`https` URLs to fetch |
| `format` | `html` (default), `xml`, or `text` |
| `show` | Result severity filter (default: `fail warn rec`) |

Bundled XSD validation is always enabled (independent of harvest `builtinSchemas`).

### Replay (local Benson)

From the repository root:

```bash
curl -sS -X POST 'http://localhost:8000/api/v1/registry-validate/voresource' \
  -F 'format=xml' \
  -F 'show=fail warn rec' \
  -F 'record=@vo-resource-file.xml;type=text/xml' \
  -o /tmp/voresource-result.xml
```

See also the **Standalone VOResource validation** section in the [project README](../../README.md).

---

## Legacy `VOResourceValidater` (rofr.ivoa.net parity)

### File

| File | Description |
|------|-------------|
| `post-res-xml-response.xml` | XML body from **`POST`** `multipart/form-data` with `format=xml`, `show=fail warn rec`, and file field `record` set to the in-repo test fixture `ivoaharvest/src/test/java/net/ivoa/registry/vores/res.xml`. Captured from **`http://rofr.ivoa.net/regvalidate/VOResourceValidater`** (May 2026). |

### Replay (legacy servlet)

```bash
curl -sS -F "format=xml" -F "show=fail warn rec" \
  -F "record=@../../ivoaharvest/src/test/java/net/ivoa/registry/vores/res.xml;type=text/xml" \
  "http://rofr.ivoa.net/regvalidate/VOResourceValidater" \
  -o post-res-xml-response.xml
```

Run from **`docs/samples/voresource-validater/`**, or use an absolute path to `res.xml`.

Benson implements the same multipart contract at `/api/v1/registry-validate/voresource`; it does **not** expose `/regvalidate/VOResourceValidater`.

### Note

The legacy servlet’s **GET** handler does not wire query parameters; interoperability is **POST**-only unless you fix the reference app.
