"""Refresh bundled IVOA XSDs from their namespace URLs.

Each ivoa.net namespace in the catalog maps to one local file. The namespace
URI always serves the current Rec-stage schema for that major version; this
command downloads that document and overwrites the matching file under
SCHEMA_ROOT. Run when a new minor Rec is published::

    benson refresh-schemas
"""

from __future__ import annotations

from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from benson.xml.catalog import NAMESPACE_SCHEMA_FILES

_IVOA_PREFIX = "http://www.ivoa.net/xml/"
_TIMEOUT_SEC = 30


def ivoa_catalog_entries() -> list[tuple[str, str]]:
    """Namespace URL and local filename for each bundled ivoa.net schema."""
    return [
        (ns, fname)
        for ns, fname in NAMESPACE_SCHEMA_FILES.items()
        if ns.startswith(_IVOA_PREFIX)
    ]


def refresh(schema_root: Path) -> tuple[list[Path], list[str]]:
    """Fetch each ivoa.net namespace URL and overwrite the local file on success.

    Returns (written paths, error messages). Existing files are left unchanged
    when a request fails or the response body is empty.
    """
    schema_root = Path(schema_root)
    written: list[Path] = []
    errors: list[str] = []
    for url, fname in ivoa_catalog_entries():
        dest = schema_root / fname
        try:
            with urlopen(url, timeout=_TIMEOUT_SEC) as resp:
                data = resp.read()
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            errors.append(f"{url}: {exc}")
            continue
        if not data:
            errors.append(f"{url}: empty response")
            continue
        dest.write_bytes(data)
        written.append(dest)
    return written, errors
