"""Run harvest OAI + IVOA + VOR pipelines and merge results."""

from __future__ import annotations

from copy import deepcopy

import httpx
from lxml import etree

from benson.config import Settings
from benson.http.validation_report import validation_result_counts
from benson.oai import phase1, phase2, phase3
from benson.session.store import HarvestRun
from benson.xml import results as R


async def execute_harvest_validation(
    run: HarvestRun,
    *,
    settings: Settings,
    client: httpx.AsyncClient,
    max_records: int,
) -> tuple[etree._ElementTree, etree._ElementTree | None]:
    timeout = settings.harvest_timeout_sec
    builtin = run.builtin_schemas
    ss = run.show_status

    run.add_status_row(
        message="OAI-PMH validation started",
        done="false",
        ok="true",
        status="running",
        phase="oai",
    )
    try:
        oai_root = await phase1.build_oai_validation(client, run.endpoint, ss, timeout=timeout, settings=settings)
        oai_tree = etree.ElementTree(oai_root)
        run.oai_validation = oai_tree
    except Exception as exc:
        raise RuntimeError(str(exc)) from exc

    run.add_status_row(
        message="OAI-PMH validation complete",
        done="false",
        ok="true",
        status="completed",
        phase="oai",
    )

    run.add_status_row(
        message="IVOA harvest profile checks started",
        done="false",
        ok="true",
        status="running",
        phase="ivoa",
    )
    ivoa_root, identify_defaults, identify_state = await phase2.build_ivoa_harvest_validation(
        client,
        run.endpoint,
        ss,
        timeout=timeout,
        builtin_schemas=builtin,
        settings=settings,
    )
    run.identify_oai_identifier = identify_defaults.get("oai_identifier")
    run.identify_title = identify_defaults.get("title")
    ivoa_tree = etree.ElementTree(ivoa_root)
    run.ivoa_validation = ivoa_tree

    run.add_status_row(
        message="IVOA harvest profile checks complete",
        done="false",
        ok="true",
        status="completed",
        phase="ivoa",
    )

    run.add_status_row(
        message="VOResource record harvest and validation started",
        done="false",
        ok="true",
        status="running",
        phase="vor",
    )
    vor_docs, harvest_stats = await phase3.harvest_voresource_documents(
        client,
        run.endpoint,
        max_records=max_records,
        timeout=timeout,
        builtin_schemas=builtin,
        settings=settings,
    )
    run.resources = vor_docs

    vor_root, _ = phase3.validate_voresource_documents(
        vor_docs,
        ss,
        builtin_schemas=builtin,
        settings=settings,
        xsl_params=identify_state,
    )
    phase3.append_harvest_failures(vor_root, harvest_stats.failures)
    vor_tree = etree.ElementTree(vor_root)
    run.vor_validation = vor_tree

    run.add_status_row(
        message="VOResource validation complete",
        done="false",
        ok="true",
        status="completed",
        phase="vor",
    )

    rr = R.registry_validation_root(status="completed", nfail="0", nwarn="0", nrec="0")
    rr.append(deepcopy(oai_root))
    rr.append(deepcopy(ivoa_root))
    rr.append(deepcopy(vor_root))

    nfail, nwarn, _npass = validation_result_counts(rr)
    rr.set("nfail", str(nfail))
    rr.set("nwarn", str(nwarn))

    merged = etree.ElementTree(rr)
    run.merged_validation = merged
    return merged, vor_tree


async def validate_oai_only(
    run: HarvestRun,
    settings: Settings,
    client: httpx.AsyncClient,
) -> etree._ElementTree:
    root = await phase1.build_oai_validation(client, run.endpoint, run.show_status, timeout=settings.harvest_timeout_sec, settings=settings)
    tree = etree.ElementTree(root)
    run.oai_validation = tree
    return tree


async def validate_ivoa_only(
    run: HarvestRun,
    settings: Settings,
    client: httpx.AsyncClient,
) -> etree._ElementTree:
    root, _defaults, _identify_state = await phase2.build_ivoa_harvest_validation(
        client,
        run.endpoint,
        run.show_status,
        timeout=settings.harvest_timeout_sec,
        builtin_schemas=run.builtin_schemas,
        settings=settings,
    )
    tree = etree.ElementTree(root)
    run.ivoa_validation = tree
    return tree


async def validate_vor_only(
    run: HarvestRun,
    settings: Settings,
    client: httpx.AsyncClient,
    max_records: int,
) -> etree._ElementTree:
    docs, _hs = await phase3.harvest_voresource_documents(
        client,
        run.endpoint,
        max_records=max_records,
        timeout=settings.harvest_timeout_sec,
        builtin_schemas=run.builtin_schemas,
        settings=settings,
    )
    run.resources = docs
    root, _ = phase3.validate_voresource_documents(
        docs,
        run.show_status,
        builtin_schemas=run.builtin_schemas,
        settings=settings,
    )
    tree = etree.ElementTree(root)
    run.vor_validation = tree
    return tree


def phase3_validate_only(
    records: dict[str, bytes],
    show_status: str,
    builtin_schemas: bool,
    settings: Settings,
    *,
    xsl_params: dict[str, str] | None = None,
) -> tuple[etree._Element, phase3.HarvestStats]:
    return phase3.validate_voresource_documents(
        records,
        show_status,
        builtin_schemas=builtin_schemas,
        settings=settings,
        xsl_params=xsl_params,
    )
