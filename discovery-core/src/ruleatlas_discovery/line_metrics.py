"""Best-effort source line metrics for discovery inventory (v1)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ruleatlas_contracts.enum_utils import enum_value

LINE_COUNT_METHOD = "v1_best_effort"
MAX_LINE_COUNT_BYTES = 2_000_000


@dataclass(frozen=True)
class LineMetrics:
    total_lines: int
    code_lines: int
    comment_lines: int
    blank_lines: int
    method: str = LINE_COUNT_METHOD
    supported: bool = True


from ruleatlas_contracts.enums import CommentStyle

from ruleatlas_discovery.file_type_registry import get_default_file_type_resolver


def infer_language_from_path(path: Path | str) -> str:
    return get_default_file_type_resolver().resolve(str(path)).language_key


def _counter_for_comment_style(comment_style: CommentStyle | str) -> Callable[[list[str]], LineMetrics]:
    style = enum_value(comment_style)
    return {
        CommentStyle.HASH.value: _count_hash_comment,
        CommentStyle.SLASH.value: _count_c_style,
        CommentStyle.HTML.value: _count_html,
        CommentStyle.SQL.value: _count_sql,
        CommentStyle.YAML.value: _count_hash_comment,
        CommentStyle.NONE.value: _count_data_lines,
        CommentStyle.UNSUPPORTED.value: _count_fallback,
    }.get(style, _count_fallback)


def _read_text_lines(path: Path) -> list[str] | None:
    try:
        if path.stat().st_size > MAX_LINE_COUNT_BYTES:
            return None
        raw = path.read_bytes()
        if b"\x00" in raw[:8192]:
            return None
        text = raw.decode("utf-8", errors="strict")
    except (OSError, UnicodeDecodeError):
        return None
    return text.splitlines()


def count_lines_in_file(
    path: Path,
    language: str | None = None,
    *,
    comment_style: CommentStyle | str | None = None,
) -> LineMetrics | None:
    """Count blank/comment/code lines for a file. Returns None when unsupported/binary."""
    resolved = get_default_file_type_resolver().resolve(str(path))
    if resolved.is_binary:
        return None
    lang = (language or resolved.language_key).lower()
    style = comment_style or resolved.comment_style
    lines = _read_text_lines(path)
    if lines is None:
        return None

    counters = {
        "python": _count_python,
        "typescript": _count_c_style,
        "tsx": _count_c_style,
        "javascript": _count_c_style,
        "jsx": _count_c_style,
        "css": _count_c_style,
        "scss": _count_c_style,
        "sql": _count_sql,
        "shell": _count_hash_comment,
        "yaml": _count_hash_comment,
        "toml": _count_hash_comment,
        "ini": _count_hash_comment,
        "properties": _count_hash_comment,
        "config": _count_hash_comment,
        "gherkin": _count_hash_comment,
        "markdown": _count_markdown,
        "html": _count_html,
        "xml": _count_html,
        "json": _count_data_lines,
    }
    if style and style not in {CommentStyle.UNSUPPORTED, CommentStyle.UNSUPPORTED.value}:
        counter = _counter_for_comment_style(style)
    else:
        counter = counters.get(lang, _count_fallback)
    return counter(lines)


def count_lines_in_text(
    text: str,
    language: str,
    *,
    comment_style: CommentStyle | str | None = None,
) -> LineMetrics:
    """Count lines from in-memory text (tests and previews)."""
    lines = text.splitlines()
    lang = language.lower()
    style = comment_style
    counters = {
        "python": _count_python,
        "typescript": _count_c_style,
        "tsx": _count_c_style,
        "javascript": _count_c_style,
        "jsx": _count_c_style,
        "css": _count_c_style,
        "scss": _count_c_style,
        "sql": _count_sql,
        "shell": _count_hash_comment,
        "yaml": _count_hash_comment,
        "toml": _count_hash_comment,
        "ini": _count_hash_comment,
        "properties": _count_hash_comment,
        "config": _count_hash_comment,
        "gherkin": _count_hash_comment,
        "markdown": _count_markdown,
        "html": _count_html,
        "xml": _count_html,
        "json": _count_data_lines,
    }
    if style and style not in {CommentStyle.UNSUPPORTED, CommentStyle.UNSUPPORTED.value}:
        counter = _counter_for_comment_style(style)
    else:
        counter = counters.get(lang, _count_fallback)
    return counter(lines)


def _finalize(lines: list[str], code: int, comment: int, blank: int) -> LineMetrics:
    total = len(lines)
    unknown = max(0, total - code - comment - blank)
    if unknown:
        code += unknown
    return LineMetrics(
        total_lines=total,
        code_lines=code,
        comment_lines=comment,
        blank_lines=blank,
    )


def _count_fallback(lines: list[str]) -> LineMetrics:
    code = comment = blank = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            blank += 1
        elif stripped.startswith(("#", "//")):
            comment += 1
        else:
            code += 1
    return _finalize(lines, code, comment, blank)


def _count_hash_comment(lines: list[str]) -> LineMetrics:
    code = comment = blank = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            blank += 1
        elif stripped.startswith("#"):
            comment += 1
        else:
            code += 1
    return _finalize(lines, code, comment, blank)


def _count_markdown(lines: list[str]) -> LineMetrics:
    """Non-blank markdown lines count as documentation content (stored in code_lines)."""
    code = blank = 0
    for line in lines:
        if not line.strip():
            blank += 1
        else:
            code += 1
    return _finalize(lines, code, 0, blank)


def _count_data_lines(lines: list[str]) -> LineMetrics:
    code = blank = 0
    for line in lines:
        if not line.strip():
            blank += 1
        else:
            code += 1
    return _finalize(lines, code, 0, blank)


def _python_triple_quote_state(stripped: str, quote: str) -> str | None:
    """Return open triple-quote marker, or None if closed on this line."""
    closed_same_line = stripped.startswith(quote) and stripped.endswith(quote) and len(stripped) >= 6
    if stripped.count(quote) < 2 or closed_same_line:
        return None
    return quote


def _close_python_triple(stripped: str, in_triple: str) -> str | None:
    if in_triple in stripped and stripped.count(in_triple) >= 2:
        return None
    return in_triple


def _try_open_python_triple(stripped: str) -> tuple[bool, str | None]:
    for quote in ('"""', "'''"):
        if stripped.startswith(quote):
            return True, _python_triple_quote_state(stripped, quote)
    return False, None


def _classify_python_line(stripped: str, in_triple: str | None) -> tuple[str, str | None]:
    """Return (bucket, updated_in_triple) where bucket is blank|comment|code."""
    if not stripped:
        return "blank", in_triple
    if in_triple:
        return "comment", _close_python_triple(stripped, in_triple)
    if stripped.startswith("#"):
        return "comment", None
    opened, next_triple = _try_open_python_triple(stripped)
    if opened:
        return "comment", next_triple
    return "code", None


def _count_python(lines: list[str]) -> LineMetrics:
    code = comment = blank = 0
    in_triple: str | None = None
    for line in lines:
        bucket, in_triple = _classify_python_line(line.strip(), in_triple)
        if bucket == "blank":
            blank += 1
        elif bucket == "comment":
            comment += 1
        else:
            code += 1
    return _finalize(lines, code, comment, blank)


def _count_sql(lines: list[str]) -> LineMetrics:
    code = comment = blank = 0
    block = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            blank += 1
            continue
        if block:
            comment += 1
            if "*/" in stripped:
                block = False
            continue
        if stripped.startswith("--"):
            comment += 1
            continue
        if stripped.startswith("/*"):
            comment += 1
            if "*/" not in stripped:
                block = True
            continue
        code += 1
    return _finalize(lines, code, comment, blank)


def _count_html(lines: list[str]) -> LineMetrics:
    code = comment = blank = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            blank += 1
            continue
        if "<!--" in stripped and "-->" in stripped:
            comment += 1
            continue
        if stripped.startswith("<!--"):
            comment += 1
            continue
        code += 1
    return _finalize(lines, code, comment, blank)


def _count_c_style(lines: list[str]) -> LineMetrics:
    code = comment = blank = 0
    block = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            blank += 1
            continue
        if block:
            comment += 1
            if "*/" in stripped:
                block = False
            continue
        if stripped.startswith("//"):
            comment += 1
            continue
        if stripped.startswith("/*"):
            comment += 1
            if "*/" not in stripped:
                block = True
            continue
        code += 1
    return _finalize(lines, code, comment, blank)
