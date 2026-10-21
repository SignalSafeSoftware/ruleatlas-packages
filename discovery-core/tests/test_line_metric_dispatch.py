"""File and preview counting share policy without merging their input boundaries."""

from pathlib import Path

import pytest
from ruleatlas_contracts.enums import CommentStyle

from ruleatlas_discovery.line_metrics import (
    MAX_LINE_COUNT_BYTES,
    count_lines_in_file,
    count_lines_in_text,
)


@pytest.mark.parametrize("language", ["python", "TSX", "sql", "html", "json", "unknown"])
@pytest.mark.parametrize("style", [None, CommentStyle.HASH, "slash", CommentStyle.UNSUPPORTED])
def test_file_and_text_dispatch_agree_when_style_is_explicit(
    tmp_path: Path,
    language: str,
    style: CommentStyle | str | None,
) -> None:
    path = tmp_path / "example.unknown"
    text = "# first\n// second\n<!-- third -->\n\nvalue😀\n"
    path.write_text(text, encoding="utf-8")
    assert count_lines_in_file(path, language, comment_style=style) == count_lines_in_text(
        text, language, comment_style=style
    )


def test_file_resolved_style_fallback_does_not_replace_text_language_policy(tmp_path: Path) -> None:
    path = tmp_path / "example.json"
    text = "# comment\nvalue\n"
    path.write_text(text, encoding="utf-8")
    file_metrics = count_lines_in_file(path, "python")
    assert file_metrics is not None and file_metrics.comment_lines == 0
    assert count_lines_in_file(path, "python", comment_style="") == file_metrics
    assert count_lines_in_text(text, "python", comment_style="").comment_lines == 1
    assert count_lines_in_file(path, "python", comment_style=CommentStyle.UNSUPPORTED) == count_lines_in_text(
        text, "python"
    )


def test_file_binary_invalid_utf8_and_size_limits_stay_outside_text_dispatch(tmp_path: Path) -> None:
    path = tmp_path / "source.py"
    for content in [b"value\x00", b"\xff", b"x" * (MAX_LINE_COUNT_BYTES + 1)]:
        path.write_bytes(content)
        assert count_lines_in_file(path) is None
    assert count_lines_in_text("value\x00", "python").code_lines == 1
