"""Invoke XSLT 1.0 stylesheets bundled under assets."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from lxml import etree


class XsltAssetsError(RuntimeError):
    """Raised when a required validation stylesheet is missing or cannot be loaded."""


def rightnow() -> str:
    """UTC timestamp for stylesheet ``rightnow`` params (legacy Java format)."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S")


def require_stylesheet(xsl_path: Path) -> Path:
    """Return ``xsl_path`` if it exists; otherwise raise with fix guidance."""
    if not xsl_path.is_file():
        raise XsltAssetsError(
            f"Required XSLT stylesheet missing: {xsl_path}. "
            "Set ASSETS_ROOT to the assets/validate directory shipped with Benson "
            "(including checkIVOAOAI.xsl / checkVOResource.xsl and their imports: "
            "testsVOResource.xsl, validationCommon.xsl, validateVocabularies.xsl). "
            "If validateVocabularies.xsl is absent, run: benson generate-vocabulary-xsl"
        )
    return xsl_path


def transform(
    xsl_path: Path,
    source_doc: etree._ElementTree | etree._Element,
    *,
    params: dict[str, str] | None = None,
) -> etree._ElementTree:
    require_stylesheet(xsl_path)
    doc = (
        source_doc
        if isinstance(source_doc, etree._ElementTree)
        else etree.ElementTree(source_doc)
    )
    try:
        tpl = etree.XSLT(etree.parse(str(xsl_path)))
    except etree.LxmlError as exc:
        raise XsltAssetsError(
            f"Failed to load XSLT stylesheet {xsl_path}: {exc}. "
            "Ensure ASSETS_ROOT contains the stylesheet and its imports "
            "(testsVOResource.xsl, validationCommon.xsl, validateVocabularies.xsl). "
            "If vocabulary checks are involved, run: benson generate-vocabulary-xsl"
        ) from exc
    kw = {k.replace(":", "_"): etree.XSLT.strparam(v) for k, v in (params or {}).items()}
    return tpl(doc, **kw)
