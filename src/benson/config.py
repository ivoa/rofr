"""Runtime configuration from environment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def project_root() -> Path:
    """Return the directory containing ``assets/schemas``."""
    here = Path(__file__).resolve()
    for candidate in (here.parents[2], Path("/app"), Path.cwd()):
        try:
            if (candidate / "assets" / "schemas").is_dir():
                return candidate
        except OSError:
            continue
    return here.parents[2]


@dataclass(slots=True)
class Settings:
    schema_root: Path
    assets_root: Path
    templates_dir: Path
    static_dir: Path
    comply_path: str | None
    oai_explorer_url: str | None
    publishers_data_dir: Path
    publishers_registry_file: Path
    registration_max_failures: int
    registration_max_warnings: int
    registration_require_builtin_schemas: bool
    searchables_regtap_sync_url: str
    searchables_adql: str
    searchables_cache_file: Path | None
    searchables_cache_dir: Path | None
    searchables_cache_max_age_sec: float | None
    harvest_timeout_sec: float
    publishers_check_timeout_sec: float
    publishers_check_concurrency: int
    parity_json_quotes: bool
    proxy_headers: bool
    forwarded_allow_ips: str
    standards_dir: Path
    oai_repository_name: str
    oai_admin_email: str
    oai_registry_identifier: str
    oai_managed_authority: str
    oai_max_records: int

    @classmethod
    def from_env(cls) -> Settings:
        root = project_root()
        sr = Path(os.environ.get("SCHEMA_ROOT", root / "assets" / "schemas")).resolve()
        ar = Path(os.environ.get("ASSETS_ROOT", root / "assets" / "validate")).resolve()
        td = Path(os.environ.get("TEMPLATES_DIR", root / "assets" / "templates")).resolve()
        sd = Path(os.environ.get("STATIC_DIR", root / "assets" / "static")).resolve()
        regtap = os.environ.get(
            "SEARCHABLES_REGTAP_SYNC_URL",
            "https://mast.stsci.edu/vo-tap/api/v0.1/registry/sync",
        ).strip()
        adql = (os.environ.get("SEARCHABLES_ADQL") or "").strip()
        cf = os.environ.get("SEARCHABLES_CACHE_FILE", "").strip()
        cd = os.environ.get("SEARCHABLES_CACHE_DIR", "").strip()
        searchables_cache_dir = (
            Path(cd).resolve() if cd else (root / "data" / "searchables").resolve()
        )
        pub_dir = Path(
            os.environ.get("PUBLISHERS_DATA_DIR", root / "data" / "publishers")
        ).resolve()
        pub_file = os.environ.get("PUBLISHERS_REGISTRY_FILE", "").strip()
        pub_registry = Path(pub_file).resolve() if pub_file else (pub_dir / "publishers.json")
        max_fail = int(os.environ.get("REGISTRATION_MAX_FAILURES", "0"))
        max_warn = int(os.environ.get("REGISTRATION_MAX_WARNINGS", "999999"))
        req_builtin = os.environ.get("REGISTRATION_REQUIRE_BUILTIN_SCHEMAS", "true").lower() in (
            "1",
            "true",
            "yes",
        )
        max_age_raw = os.environ.get("SEARCHABLES_CACHE_MAX_AGE_SEC", "").strip()
        max_age: float | None
        if max_age_raw:
            max_age = float(max_age_raw)
        else:
            max_age = None
        proxy_headers = os.environ.get("BENSON_PROXY_HEADERS", "true").lower() in (
            "1",
            "true",
            "yes",
        )
        forwarded_allow_ips = os.environ.get("FORWARDED_ALLOW_IPS", "*").strip() or "*"
        standards_dir = Path(
            os.environ.get("STANDARDS_DIR", root / "assets" / "standards")
        ).resolve()
        oai_repository_name = os.environ.get(
            "OAI_REPOSITORY_NAME", "IVOA Registry of Registries"
        ).strip()
        oai_admin_email = os.environ.get("OAI_ADMIN_EMAIL", "registry@ivoa.net").strip()
        oai_registry_identifier = os.environ.get(
            "OAI_REGISTRY_IDENTIFIER", "ivo://ivoa.net/rofr"
        ).strip()
        oai_managed_authority = os.environ.get("OAI_MANAGED_AUTHORITY", "ivoa.net").strip()
        oai_max_records = int(os.environ.get("OAI_MAX_RECORDS", "100"))
        return cls(
            schema_root=sr,
            assets_root=ar,
            templates_dir=td,
            static_dir=sd,
            comply_path=os.environ.get("COMPLY_PATH") or None,
            oai_explorer_url=os.environ.get("OAI_EXPLORER_URL") or None,
            publishers_data_dir=pub_dir,
            publishers_registry_file=pub_registry,
            registration_max_failures=max_fail,
            registration_max_warnings=max_warn,
            registration_require_builtin_schemas=req_builtin,
            searchables_regtap_sync_url=regtap,
            searchables_adql=adql,
            searchables_cache_file=Path(cf).resolve() if cf else None,
            searchables_cache_dir=searchables_cache_dir,
            searchables_cache_max_age_sec=max_age,
            harvest_timeout_sec=float(os.environ.get("HARVEST_TIMEOUT_SEC", "240")),
            publishers_check_timeout_sec=float(
                os.environ.get("PUBLISHERS_CHECK_TIMEOUT_SEC", "30")
            ),
            publishers_check_concurrency=int(
                os.environ.get("PUBLISHERS_CHECK_CONCURRENCY", "5")
            ),
            parity_json_quotes=os.environ.get("BENSON_PARITY_JSON", "").lower()
            in ("1", "true", "yes"),
            proxy_headers=proxy_headers,
            forwarded_allow_ips=forwarded_allow_ips,
            standards_dir=standards_dir,
            oai_repository_name=oai_repository_name,
            oai_admin_email=oai_admin_email,
            oai_registry_identifier=oai_registry_identifier,
            oai_managed_authority=oai_managed_authority,
            oai_max_records=oai_max_records,
        )
