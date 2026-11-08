"""Render validation result XML as human-readable HTML."""

from __future__ import annotations

import re
from dataclasses import dataclass
from html import escape

from lxml import etree

_SECTION_LABELS: dict[str, str] = {
    "OAIValidation": "OAI-PMH conformance",
    "HarvestValidation": "IVOA harvest profile",
    "VOResourceValidation": "VOResource records",
}

_SECTION_PREFIX: dict[str, str] = {
    "OAIValidation": "oai",
    "HarvestValidation": "harvest",
    "VOResourceValidation": "vor",
}


@dataclass(frozen=True)
class _Test:
    item: str
    status: str
    message: str


@dataclass(frozen=True)
class _Query:
    name: str
    subtitle: str
    tests: tuple[_Test, ...]
    anchor: str
    ignored_errors: tuple[str, ...] = ()

    @property
    def status(self) -> str:
        if any(t.status == "fail" for t in self.tests):
            return "fail"
        if any(t.status == "warn" for t in self.tests):
            return "warn"
        return "pass"


@dataclass(frozen=True)
class _Section:
    tag: str
    label: str
    anchor: str
    queries: tuple[_Query, ...]

    @property
    def fail_count(self) -> int:
        return sum(1 for q in self.queries if q.status == "fail")

    @property
    def warn_count(self) -> int:
        return sum(1 for q in self.queries if q.status == "warn")

    @property
    def pass_count(self) -> int:
        return sum(1 for q in self.queries if q.status == "pass")


def _local_tag(el: etree._Element) -> str:  # noqa: SLF001
    tag = el.tag
    if not isinstance(tag, str):
        return ""
    if tag.startswith("{"):
        return tag.rpartition("}")[2]
    return tag


def _text(el: etree._Element) -> str:  # noqa: SLF001
    return (el.text or "").strip()


def _slug(prefix: str, label: str, idx: int) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")[:48]
    return f"val-{prefix}-{idx}-{base}" if base else f"val-{prefix}-{idx}"


def _parse_query(el: etree._Element, *, prefix: str, idx: int) -> _Query:  # noqa: SLF001
    name = el.get("name") or el.get("recordName") or "test"
    bits: list[str] = []
    if opts := el.get("options"):
        bits.append(opts)
    if ivo_id := el.get("ivo-id"):
        bits.append(ivo_id)
    tests = tuple(
        _Test(
            item=t.get("item") or "",
            status=(t.get("status") or "pass").lower(),
            message=_text(t),
        )
        for t in el
        if _local_tag(t) == "test"
    )
    ignored_raw = el.get("ignoredErrors") or ""
    ignored_errors = tuple(part for part in ignored_raw.split(",") if part)
    return _Query(
        name=name,
        subtitle=" · ".join(bits),
        tests=tests,
        anchor=_slug(prefix, name, idx),
        ignored_errors=ignored_errors,
    )


def _parse_section(el: etree._Element) -> _Section:  # noqa: SLF001
    tag = _local_tag(el)
    prefix = _SECTION_PREFIX.get(tag, "sec")
    queries = tuple(
        _parse_query(q, prefix=prefix, idx=i)
        for i, q in enumerate(el)
        if _local_tag(q) == "testQuery"
    )
    return _Section(
        tag=tag,
        label=_SECTION_LABELS.get(tag, tag),
        anchor=f"val-section-{prefix}",
        queries=queries,
    )


def _parse_report(root: etree._Element) -> tuple[_Section, ...]:  # noqa: SLF001
    tag = _local_tag(root)
    if tag == "RegistryValidation":
        return tuple(_parse_section(child) for child in root if _local_tag(child) in _SECTION_LABELS)
    if tag in _SECTION_LABELS:
        return (_parse_section(root),)
    return ()


def _counts(sections: tuple[_Section, ...]) -> tuple[int, int, int]:
    fails = warns = passes = 0
    for section in sections:
        fails += section.fail_count
        warns += section.warn_count
        passes += section.pass_count
    return fails, warns, passes


def validation_result_counts(root: etree._Element) -> tuple[int, int, int]:  # noqa: SLF001
    """Return (nfail, nwarn, npass) at testQuery level — same logic as the HTML report."""
    return _counts(_parse_report(root))


def _badge(status: str, text: str) -> str:
    return f'<span class="val-badge val-badge--{escape(status)}">{escape(text)}</span>'


def _render_summary(fails: int, warns: int, passes: int) -> str:
    if fails:
        tone = "fail"
        headline = f"{fails} failure{'s' if fails != 1 else ''}"
    elif warns:
        tone = "warn"
        headline = f"{warns} warning{'s' if warns != 1 else ''}"
    else:
        tone = "pass"
        headline = "All checks passed"
    parts = [headline]
    if fails and warns:
        parts.append(f"{warns} warning{'s' if warns != 1 else ''}")
    if passes:
        parts.append(f"{passes} passed")
    return (
        f'<div class="val-summary val-summary--{tone}" role="status">'
        f'<p class="val-summary-headline">{escape(", ".join(parts))}</p>'
        "</div>"
    )


def _render_toolbar(fails: int, warns: int, passes: int) -> str:
    total = fails + warns + passes
    return f"""
<div class="val-toolbar" role="toolbar" aria-label="Filter results">
  <span class="val-toolbar-label">Show</span>
  <label class="val-filter" for="val-filter-failures">Failures ({fails})</label>
  <label class="val-filter" for="val-filter-passed">Passed ({passes})</label>
  <label class="val-filter" for="val-filter-all">All ({total})</label>
</div>
<input type="radio" name="val-filter" id="val-filter-failures" class="val-filter-input" checked hidden>
<input type="radio" name="val-filter" id="val-filter-passed" class="val-filter-input" hidden>
<input type="radio" name="val-filter" id="val-filter-all" class="val-filter-input" hidden>
"""


def _render_jump_nav(sections: tuple[_Section, ...]) -> str:
    items: list[str] = []
    for section in sections:
        if not section.queries:
            continue
        badges: list[str] = []
        if section.fail_count:
            badges.append(f"{section.fail_count} failed")
        if section.warn_count:
            badges.append(f"{section.warn_count} warnings")
        if section.pass_count and not section.fail_count and not section.warn_count:
            badges.append("all passed")
        meta = f' <span class="val-jump-meta">({escape(", ".join(badges))})</span>' if badges else ""
        items.append(
            f'<li class="val-jump-section">'
            f'<a href="#{escape(section.anchor)}">{escape(section.label)}</a>{meta}'
        )
        for query in section.queries:
            if query.status == "fail":
                items.append(
                    f'<li class="val-jump-fail">'
                    f'<a href="#{escape(query.anchor)}">{escape(query.name)}</a></li>'
                )
    if not items:
        return ""
    return (
        '<nav class="val-jump" aria-label="Jump to results">'
        '<p class="val-jump-title">Jump to</p>'
        f'<ul class="val-jump-list">{"".join(items)}</ul>'
        "</nav>"
    )


def _render_tests(tests: tuple[_Test, ...]) -> str:
    if not tests:
        return '<p class="val-empty">No individual test results recorded.</p>'
    rows: list[str] = []
    for test in tests:
        if test.status == "pass" and test.item == "summary":
            continue
        item = escape(test.item) if test.item else "test"
        msg = escape(test.message) if test.message else ("Passed" if test.status == "pass" else test.status)
        rows.append(
            f'<li class="val-test val-test--{escape(test.status)}">'
            f'<code class="val-test-item">{item}</code> '
            f'<span class="val-test-msg">{msg}</span></li>'
        )
    if not rows:
        return '<p class="val-empty">Summary check passed.</p>'
    return f'<ul class="val-tests">{"".join(rows)}</ul>'


def _render_ignored_note(errors: tuple[str, ...]) -> str:
    if not errors:
        return ""
    label = "code" if len(errors) == 1 else "codes"
    codes = ", ".join(f"<code>{escape(error)}</code>" for error in errors)
    return f'<p class="val-ignored-note">Ignored error {label}: {codes}</p>'


def _render_query(query: _Query) -> str:
    status = query.status
    open_attr = ' open' if status in ("fail", "warn") else ""
    subtitle = f' <span class="val-query-sub">{escape(query.subtitle)}</span>' if query.subtitle else ""
    badge = _badge(status, status)
    ignored = _render_ignored_note(query.ignored_errors)
    return (
        f'<details id="{escape(query.anchor)}" class="val-query val-query--{status}"{open_attr}>'
        f"<summary>{escape(query.name)}{subtitle} {badge}</summary>"
        f"{ignored}{_render_tests(query.tests)}"
        "</details>"
    )


def _render_passed_group(queries: tuple[_Query, ...]) -> str:
    if not queries:
        return ""
    n = len(queries)
    body = "".join(_render_query(q) for q in queries)
    return (
        f'<details class="val-passed-group">'
        f'<summary>{n} passed check{"s" if n != 1 else ""}</summary>'
        f'<div class="val-passed-group-body">{body}</div>'
        "</details>"
    )


def _render_section(section: _Section) -> str:
    open_attr = " open" if section.fail_count or section.warn_count else ""
    parts: list[str] = []
    if section.fail_count:
        parts.append(_badge("fail", f"{section.fail_count} failed"))
    if section.warn_count:
        parts.append(_badge("warn", f"{section.warn_count} warnings"))
    if section.pass_count:
        parts.append(_badge("pass", f"{section.pass_count} passed"))
    if not parts:
        parts.append(_badge("pass", "all passed"))

    issues = [q for q in section.queries if q.status in ("fail", "warn")]
    passed = [q for q in section.queries if q.status == "pass"]
    body = "".join(_render_query(q) for q in issues) + _render_passed_group(tuple(passed))
    if not body:
        body = '<p class="val-empty">No checks in this section.</p>'

    return (
        f'<details id="{escape(section.anchor)}" class="val-section"{open_attr}>'
        f'<summary><h3 class="val-section-label">{escape(section.label)}</h3> '
        f'{" ".join(parts)}</summary>'
        f'<div class="val-section-body">{body}</div>'
        "</details>"
    )


def render_validation_report(tree: etree._ElementTree) -> str:  # noqa: SLF001
    """Turn a validation XML tree into an HTML report fragment."""
    sections = _parse_report(tree.getroot())
    if not sections:
        return '<p class="val-empty">No validation results to display.</p>'

    fails, warns, passes = validation_result_counts(tree.getroot())
    jump = _render_jump_nav(sections)
    body = "".join(
        [
            _render_summary(fails, warns, passes),
            _render_toolbar(fails, warns, passes),
            "".join(_render_section(section) for section in sections),
        ]
    )
    if jump:
        return (
            f'<div class="val-report">'
            f'<div class="val-report-body">{body}</div>'
            f"{jump}"
            f"</div>"
        )
    return f'<div class="val-report"><div class="val-report-body">{body}</div></div>'
