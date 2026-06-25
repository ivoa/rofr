"""CLI entry point for running the Benson HTTP server."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys


def _dev_mode_enabled() -> bool:
    return os.environ.get("BENSON_DEV", "").lower() in ("1", "true", "yes")


def _apply_proxy_settings(*, enabled: bool, forwarded_allow_ips: str | None) -> None:
    os.environ["BENSON_PROXY_HEADERS"] = "true" if enabled else "false"
    if forwarded_allow_ips is not None:
        os.environ["FORWARDED_ALLOW_IPS"] = forwarded_allow_ips


def _add_serve_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--reload",
        "-r",
        action="store_true",
        help="Enable auto-reload when source or asset files change (development)",
    )
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--proxy-headers",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Trust X-Forwarded-Proto and X-Forwarded-Host from reverse proxies "
            "(default: enabled). Applied in the app so url_for and request.url are correct."
        ),
    )
    parser.add_argument(
        "--forwarded-allow-ips",
        default=None,
        metavar="IPS",
        help=(
            "Comma-separated IPs/networks allowed to set forwarded headers "
            "(default: FORWARDED_ALLOW_IPS env or '*'). Passed to uvicorn when --proxy-headers is on."
        ),
    )


def _run_serve(args: argparse.Namespace) -> None:
    import uvicorn

    from benson.config import project_root

    forwarded = args.forwarded_allow_ips
    if forwarded is None:
        forwarded = os.environ.get("FORWARDED_ALLOW_IPS", "*")

    _apply_proxy_settings(enabled=args.proxy_headers, forwarded_allow_ips=forwarded)

    reload = args.reload or _dev_mode_enabled()
    root = project_root()
    reload_dirs = [str(root / "src"), str(root / "assets")] if reload else None

    uvicorn.run(
        "benson.app:create_app",
        factory=True,
        host=args.host,
        port=args.port,
        reload=reload,
        reload_dirs=reload_dirs,
        proxy_headers=False,
    )


def _run_check_publishers(args: argparse.Namespace) -> None:
    from dataclasses import asdict

    import httpx

    from benson.config import Settings
    from benson.registry.publishers_check import check_publishers
    from benson.registry.publishers_store import PublisherStore

    settings = Settings.from_env()
    timeout = (
        args.timeout
        if args.timeout is not None
        else settings.publishers_check_timeout_sec
    )
    store = PublisherStore.from_settings(settings)

    async def run() -> list:
        async with httpx.AsyncClient(http2=False) as client:
            results = await check_publishers(
                client,
                store,
                timeout=timeout,
                concurrency=settings.publishers_check_concurrency,
            )
            if not args.dry_run:
                await store.annotate_checks(results)
            return results

    results = asyncio.run(run())

    if args.json:
        print(json.dumps([asdict(r) for r in results], indent=2))
    else:
        counts: dict[str, int] = {}
        for result in results:
            counts[result.status] = counts.get(result.status, 0) + 1
            line = f"{result.oai_identifier}\t{result.status}"
            if result.detail:
                line += f"\t{result.detail}"
            print(line)
        summary = ", ".join(f"{n} {status}" for status, n in sorted(counts.items()))
        print(f"Checked {len(results)} publishers: {summary}")

    if args.dry_run:
        return
    if any(result.status != "ok" for result in results):
        sys.exit(1)


def _run_sync_searchables(args: argparse.Namespace) -> None:
    import httpx

    from benson.config import Settings
    from benson.service.searchables_regtap import refresh_searchables_cache

    settings = Settings.from_env()
    timeout = min(60.0, settings.harvest_timeout_sec)
    if settings.searchables_cache_file is None and settings.searchables_cache_dir is None:
        print(
            "No searchables cache configured (SEARCHABLES_CACHE_FILE or SEARCHABLES_CACHE_DIR).",
            file=sys.stderr,
        )
        sys.exit(2)

    async def run() -> int:
        async with httpx.AsyncClient(http2=False) as client:
            rows = await refresh_searchables_cache(client, settings, timeout_sec=timeout)
            return len(rows)

    count = asyncio.run(run())
    if args.json:
        print(json.dumps({"status": "ok", "count": count}))
    else:
        print(f"Searchables cache refreshed ({count} registries).")


def main() -> None:
    if len(sys.argv) == 1 or (
        len(sys.argv) > 1
        and sys.argv[1] not in ("serve", "check-publishers", "sync-searchables")
    ):
        sys.argv.insert(1, "serve")

    parser = argparse.ArgumentParser(description="Benson registry validator.")
    subparsers = parser.add_subparsers(dest="command")

    serve_parser = subparsers.add_parser("serve", help="Run the HTTP server (default)")
    _add_serve_arguments(serve_parser)

    check_parser = subparsers.add_parser(
        "check-publishers",
        help="Probe registered publishers via OAI Identify",
    )
    check_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report results without updating publishers.json",
    )
    check_parser.add_argument(
        "--json",
        action="store_true",
        help="Print results as JSON",
    )
    check_parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        metavar="SEC",
        help="Per-request timeout (default: PUBLISHERS_CHECK_TIMEOUT_SEC or 30)",
    )

    sync_parser = subparsers.add_parser(
        "sync-searchables",
        help="Fetch full searchable registries from RegTAP and write the CSV cache",
    )
    sync_parser.add_argument(
        "--json",
        action="store_true",
        help="Print result as JSON",
    )

    args = parser.parse_args()
    if args.command in (None, "serve"):
        _run_serve(args)
    elif args.command == "check-publishers":
        _run_check_publishers(args)
    elif args.command == "sync-searchables":
        _run_sync_searchables(args)
    else:
        parser.error(f"unknown command: {args.command}")


if __name__ == "__main__":
    main()
