# Production OAI behind a reverse proxy

Deployers run Benson behind TLS terminators or load balancers. Harvesters learn your OAI base from **`Identify`**: the `baseURL` element, every `oai:request`, and the Registry **`accessURL`** in embedded metadata. Benson derives all of these from the incoming HTTP request (`request.url_for("oai")`). There is no separate public-URL environment variable.

If the app only sees `http://127.0.0.1:8000`, OAI responses will advertise that address and harvesters will fail or target the wrong host.

## Settings

| Name | Default | Purpose |
|------|---------|---------|
| `BENSON_PROXY_HEADERS` | `true` | Enable forwarded-header handling (Docker and `benson` CLI default). |
| `FORWARDED_ALLOW_IPS` | `*` | Which client addresses may set `X-Forwarded-*` (uvicorn `trusted_hosts`). **Narrow this in production.** |

CLI equivalents: `benson --proxy-headers` / `--no-proxy-headers`, `benson --forwarded-allow-ips 10.0.0.0/8,127.0.0.1`.

When enabled, Benson applies:

1. **Uvicorn `ProxyHeadersMiddleware`** — honours `X-Forwarded-Proto` (and related) from trusted IPs.
2. **`ForwardedHostMiddleware`** — maps `X-Forwarded-Host` onto the ASGI `Host` header so Starlette builds correct absolute URLs.

## Proxy requirements

Terminate HTTPS at the edge and forward to Benson with at least:

```http
X-Forwarded-Proto: https
X-Forwarded-Host: rofr.example.org
```

Use the hostname and scheme **clients** use. `X-Forwarded-For` is optional (logging only).

Public harvest URL example: `https://rofr.example.org/oai`. The proxy should expose `/oai` at that path unless you deliberately use a path prefix (then forwarded host and routing must still match what harvesters call).

## Verify after deploy

Set `ORIGIN` to your public OAI base (no trailing slash), e.g. `https://rofr.example.org/oai`.

**1. `baseURL`**

```bash
curl -sS "${ORIGIN}?verb=Identify" \
  | xmllint --xpath 'string(//*[local-name()="baseURL"])' -
```

Must print exactly `${ORIGIN}`.

**2. `oai:request`**

```bash
curl -sS "${ORIGIN}?verb=Identify" \
  | xmllint --xpath 'string(//*[local-name()="request"])' -
```

Must use the same public host and `https` if the site is HTTPS—not `localhost`, a container name, or bare `http://` behind TLS.

**3. Registry harvest URL in Identify**

The `vg:Registry` resource in the Identify `description` must list the same OAI base in its Registry harvest `accessURL` as in `baseURL`.

**4. Optional — paged `ListRecords`**

For large catalogs, call `ListRecords` with `metadataPrefix=ivo_vor` and follow `resumptionToken` until done. Each response’s `request` element should keep the public host.

## Troubleshooting

| Symptom | Likely cause |
|---------|----------------|
| `baseURL` shows `http://` on an HTTPS site | Proxy not sending `X-Forwarded-Proto`, or proxy headers disabled |
| Wrong hostname (internal name) | Missing or wrong `X-Forwarded-Host` |
| Correct on `curl localhost:8000`, wrong on public URL | Edge proxy not forwarding headers, or `FORWARDED_ALLOW_IPS` excludes the proxy hop |
| Local dev without a proxy | `benson --no-proxy-headers` or `BENSON_PROXY_HEADERS=false` |

Spoofed `X-Forwarded-*` from arbitrary clients is why production should set `FORWARDED_ALLOW_IPS` to your proxy’s address(es), not `*`.

## Related

- Environment variable table: [project README § Environment](../README.md#environment)
- OAI sets and harvest examples: [docs/README § OAI endpoints](README.md#oai-endpoints)
