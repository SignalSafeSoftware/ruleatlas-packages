from __future__ import annotations

from datetime import UTC, datetime

__all__ = [
    "bullet_list",
    "report_header",
    "section",
    "table",
    "utc_timestamp_label",
]


def utc_timestamp_label(generated_at: datetime | None = None) -> str:
    moment = generated_at or datetime.now(UTC)
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def report_header(
    project_name: str,
    report_title: str,
    generated_at: datetime | None = None,
    *,
    latest_scan_line: str | None = None,
    analysis_version_line: str | None = None,
    analysis_version_id: str | None = None,
    analysis_version_number: int | None = None,
    is_active_analysis_version: bool | None = None,
    linked_scan_run_id: str | None = None,
    scope_label: str | None = None,
) -> str:
    lines = [
        f"# {report_title}",
        "",
        f"**Project:** {project_name}",
        f"**Generated:** {utc_timestamp_label(generated_at)}",
    ]
    if scope_label:
        lines.append(f"**Scope:** {scope_label}")
    if analysis_version_id:
        lines.append(f"**Analysis version ID:** `{analysis_version_id}`")
    if analysis_version_number is not None:
        lines.append(f"**Analysis version number:** v{analysis_version_number}")
    if is_active_analysis_version is not None:
        status_label = "Active (project default)" if is_active_analysis_version else "Historical (not project default)"
        lines.append(f"**Analysis version status:** {status_label}")
    if analysis_version_line:
        lines.append(f"**Analysis version:** {analysis_version_line}")
    if linked_scan_run_id:
        lines.append(f"**Linked scan run:** `{linked_scan_run_id}`")
    if latest_scan_line:
        lines.append(f"**Latest scan:** {latest_scan_line}")
    lines.append("")
    return "\n".join(lines)


def section(title: str, body: str) -> str:
    trimmed = body.strip()
    if not trimmed:
        return f"## {title}\n\n_No data._\n"
    return f"## {title}\n\n{trimmed}\n"


def bullet_list(items: list[str]) -> str:
    if not items:
        return "_No items._"
    return "\n".join(f"- {item}" for item in items)


def table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "_No rows._"
    header_line = "| " + " | ".join(headers) + " |"
    divider = "| " + " | ".join("---" for _ in headers) + " |"
    body_lines = ["| " + " | ".join(_escape_cell(cell) for cell in row) + " |" for row in rows]
    return "\n".join([header_line, divider, *body_lines])


def _escape_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
