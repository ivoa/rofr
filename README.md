<p align="center">
  <img src="docs/images/logo.png" alt="Benson logo" width="240">
</p>

# Benson

IVOA registry validator: OAI-PMH harvest checks, IVOA four-GET profile, VOResource XSD/XSLT validation.

Web UI colors and typography follow [ivoa.net](https://ivoa.net); design tokens live in [`assets/static/css/ivoa-theme.css`](assets/static/css/ivoa-theme.css).

## Run

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
source .venv/bin/activate
```

Production (no reload):

```bash
benson
# Proxy headers are on by default (--proxy-headers). Disable with: benson --no-proxy-headers
# or: uvicorn benson.app:create_app --factory --host 0.0.0.0 --port 8000 --proxy-headers
```

Development (auto-reload on changes under `src/` and `assets/`):

```bash
benson --reload
# or: BENSON_DEV=1 benson
# or: uvicorn benson.app:create_app --factory --host 0.0.0.0 --port 8000 --reload --reload-dir src --reload-dir assets
```

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET, POST | `/validator`, `/regvalidate` | Async harvest validation form |
| POST | `/validator/jobs` | Start validation job |
| GET | `/oai` | IVOA standards OAI-PMH catalog from `assets/standards` |
| GET | `/list-publishers` | Publishers OAI XML catalog |
| GET | `/api/v1/registry/publishers` | Publishers registry (JSON) |
| GET, POST | `/api/v1/registry-validate/harvest` | Harvest validation API |
| POST | `/api/v1/registry-validate/voresource` | VOResource validation API |

### Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `SCHEMA_ROOT` | `./assets/schemas` | Bundled XSD schemas |
| `ASSETS_ROOT` | `./assets/validate` | XSLT validation stylesheets |
| `STANDARDS_DIR` | `./assets/standards` | IVOA standards records (indexed at `/oai`) |
| `OAI_REPOSITORY_NAME` | `IVOA Registry of Registries` | OAI Identify repository name |
| `OAI_ADMIN_EMAIL` | `registry@ivoa.net` | OAI admin contact |
| `OAI_REGISTRY_IDENTIFIER` | `ivo://ivoa.net/rofr` | OAI registry identifier |
| `OAI_MANAGED_AUTHORITY` | `ivoa.net` | OAI managed authority |
| `OAI_MAX_RECORDS` | `100` | Max records per OAI list response |
| `TEMPLATES_DIR` | `./assets/templates` | Jinja templates |
| `STATIC_DIR` | `./assets/static` | Static assets |
| `PUBLISHERS_DATA_DIR` | `./data/publishers` | Publishers registry data directory |
| `PUBLISHERS_REGISTRY_FILE` | `./data/publishers/publishers.json` | Publishers registry JSON file |
| `SEARCHABLES_CACHE_DIR` | `./data/searchables` | RegTAP CSV cache directory (`registries.csv`) |
| `SEARCHABLES_CACHE_MAX_AGE_SEC` | — | Cache TTL; unset means no expiry |
| `REGISTRATION_MAX_FAILURES` | `0` | Max failures allowed for registration |
| `REGISTRATION_MAX_WARNINGS` | `999999` | Max warnings allowed for registration |
| `REGISTRATION_REQUIRE_BUILTIN_SCHEMAS` | on | Require built-in XSD schemas for registration |
| `BENSON_PROXY_HEADERS` | on | Enable proxy headers (fixes template `url_for` behind a reverse proxy) |
| `FORWARDED_ALLOW_IPS` | `*` | Trusted proxy IPs (tighten in production) |
| `COMPLY_PATH` | — | Optional comply path |
| `LOG_LEVEL` | `INFO` | Logging level |
| `BENSON_PARITY_JSON` | off | Enable JSON parity mode (`=1` to enable) |
| `BENSON_EXPOSE_ERRORS` | off | Expose error details in responses (debug only; `=1` to enable) |

## Deployers

Deployers who operate a live Registry of Registries instance should run the publisher liveness check periodically:

```bash
benson check-publishers
```

The command reads `PUBLISHERS_REGISTRY_FILE`, sends one lightweight OAI-PMH `Identify` request to each registered publisher endpoint, and writes status metadata back into the publishers JSON file. It does not harvest records; its intent is to catch entries whose services have gone stale, become unreachable, changed identity, or stopped operating.

Typical usage is from cron or another deployment scheduler, using the same environment and volume mount as the running Benson service:

```bash
PUBLISHERS_REGISTRY_FILE=/data/publishers/publishers.json benson check-publishers
```

Useful options:

- `--dry-run` reports results without updating `publishers.json`.
- `--json` prints machine-readable results for logs or monitoring.
- `--timeout SEC` overrides `PUBLISHERS_CHECK_TIMEOUT_SEC`.

Any non-`ok` publisher causes a non-zero exit code unless `--dry-run` is used, which makes the command suitable for alerting. The main page displays the last check status and timestamp once the command has populated `last_checked_at` and `check_status`.

### Built-in XSD catalog (`builtinSchemas`)

When the validator form enables **Use built-in XSD schemas**, phase 2 (IVOA four GETs) and phase 3 (harvested records) use the bundled namespace map in [`src/benson/xml/catalog.py`](src/benson/xml/catalog.py) under `SCHEMA_ROOT` (default [`assets/schemas/`](assets/schemas/)).

OAI responses are validated in two steps: embedded `description` / `metadata` / `about` payloads are checked against the appropriate IVOA XSDs (Registry Interface records use [`benson-ivoa-bundle.xsd`](assets/schemas/benson-ivoa-bundle.xsd) so `xsi:type` extensions such as `vg:Registry` resolve), then the OAI-PMH envelope is checked via [`benson-oai-bundle.xsd`](assets/schemas/benson-oai-bundle.xsd). Imports are resolved locally (no network). This matches the regvalidate functional contract intent; validating against `OAI-v2.xsd` alone is not sufficient for registry `Identify` responses that embed `ri:Resource` metadata.

**Developer guide:** [docs/schemas-and-validation-assets.md](docs/schemas-and-validation-assets.md) — directory layout, bundle composition, namespace table, XSLT assets (`assets/validate/`), standards catalog (`assets/standards/`), and how each validation phase uses them.

## Tests

After installing with `.[dev]` (see **Run** above):

```bash
pytest
```

On Debian/Ubuntu, install system libraries for `lxml` if needed: `apt-get install libxml2 libxslt1.1`.

## Docker

Build and run locally:

```bash
docker build -t benson:local .
docker run --rm -p 8000:8000 benson:local
```

Pull from GitHub Container Registry (after CI has pushed an image):

```bash
docker login ghcr.io
docker pull ghcr.io/my-org/benson:latest
```

### Docker Compose

[`docker-compose.yml`](docker-compose.yml) runs Benson with host directories for registry catalogue data:

| Host path | Container path | Purpose |
|-----------|----------------|---------|
| `./data/searchables/` | `/data/searchables` | CSV exports of full searchable registries (RegTAP). Set `SEARCHABLES_CACHE_DIR` to this path. |
| `./data/publishers/` | `/data/publishers` | Registered publishing registries (`publishers.json`). Served as OAI XML at `/list-publishers`. |

Example layout:

```text
data/
  searchables/
    registries.csv          # RegTAP sync export
  publishers/
    publishers.json         # canonical registry list (OAI XML generated at /list-publishers)
```

```bash
docker compose up --build
```

Then open `http://localhost:8000/` (landing page) or `http://localhost:8000/validator`.

When the cache directory is empty, searchables are fetched live from `SEARCHABLES_REGTAP_SYNC_URL` on the first home page load (or via `benson sync-searchables`), and the CSV response is written to `SEARCHABLES_CACHE_DIR/registries.csv` (or `SEARCHABLES_CACHE_FILE`). Subsequent loads use the cache until `SEARCHABLES_CACHE_MAX_AGE_SEC` expires. An empty `publishers.json` is created automatically; register registries via the validator after a successful dry-run validation.

To warm the searchables cache without opening the home page:

```bash
SEARCHABLES_CACHE_DIR=./data/searchables benson sync-searchables
```

### Registering and updating publishing registries

After a successful validation (zero failures, built-in XSD schemas enabled), the validator offers registration with the Registry of Registries. Submit the registry’s IVOA identifier and title; Benson stores the entry in `publishers.json` and serves it at `/list-publishers`.

**Updates** use the same flow: validate the registry’s current OAI endpoint (for example after a host or domain change), then submit the same IVOA identifier and an updated title if needed. Benson detects the existing listing and updates `harvest_access_url` and `title` instead of rejecting the submission. The original `registered_at` timestamp is preserved; `updated_at` records when the listing last changed.

Requirements for updates:

- Validation must pass under the same policy as new registration (`REGISTRATION_MAX_FAILURES`, built-in schemas, and so on).
- The live Identify identifier must match the stored IVOA identifier (prevents hijacking another listing).
- The validated endpoint must not already belong to a different registered identifier.

The IVOA identifier itself cannot be changed through this path; a registry with a new identity is a new listing.

`benson check-publishers` may report URL drift in `check_detail` when a live harvest URL differs from the stored value. It does not update the catalogue automatically — re-validate and submit an update through the validator instead.
