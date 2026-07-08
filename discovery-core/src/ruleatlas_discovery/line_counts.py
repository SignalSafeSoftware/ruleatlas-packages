"""Line count aggregation helpers."""

from __future__ import annotations

from collections import defaultdict

from ruleatlas_discovery.constants import (
    NO_EXTENSION,
    NO_EXTENSION_FILE_TYPE,
    MappingSource,
)
from ruleatlas_discovery.file_types import FileTypeResolver, get_default_file_type_resolver
from ruleatlas_discovery.models import DiscoveryFile, FileTypeSummary, LineCountSummary


def _line_split(row: DiscoveryFile) -> tuple[int, int, int, int]:
    total = row.line_count or 0
    code = row.code_lines
    comment = row.comment_lines
    blank = row.blank_lines
    if code is None and comment is None and blank is None and total:
        return total, total, 0, 0
    return total, code or 0, comment or 0, blank or 0


def aggregate_line_counts(files: list[DiscoveryFile]) -> LineCountSummary:
    total_lines = code_lines = comment_lines = blank_lines = 0
    for row in files:
        total, code, comment, blank = _line_split(row)
        total_lines += total
        code_lines += code
        comment_lines += comment
        blank_lines += blank
    return LineCountSummary(
        total_lines=total_lines,
        code_lines=code_lines,
        comment_lines=comment_lines,
        blank_lines=blank_lines,
        files=len(files),
    )


def aggregate_line_counts_by_file_type(
    files: list[DiscoveryFile],
    *,
    resolver: FileTypeResolver | None = None,
) -> list[FileTypeSummary]:
    resolver = resolver or get_default_file_type_resolver()
    grouped: dict[tuple[str, str, str, str, str], dict[str, int | str]] = {}

    for row in files:
        resolved = resolver.resolve(row.path)
        bucket = row.bucket or resolved.default_bucket_hint
        group_key = (
            resolved.language,
            resolved.extension,
            resolved.file_type,
            resolved.file_kind,
            bucket,
        )
        total, code, comment, blank = _line_split(row)
        size_bytes = int(row.size_bytes or 0)

        if group_key not in grouped:
            grouped[group_key] = {
                "language": resolved.language,
                "extension": resolved.extension,
                "file_type": resolved.file_type,
                "file_kind": resolved.file_kind,
                "bucket": bucket,
                "mapping_source": resolved.mapping_source,
                "mapping_pattern": resolved.mapping_pattern,
                "files": 0,
                "size_bytes": 0,
                "total_lines": 0,
                "code_lines": 0,
                "comment_lines": 0,
                "blank_lines": 0,
            }
        item = grouped[group_key]
        item["files"] = int(item["files"]) + 1
        item["size_bytes"] = int(item["size_bytes"]) + size_bytes
        item["total_lines"] = int(item["total_lines"]) + total
        item["code_lines"] = int(item["code_lines"]) + code
        item["comment_lines"] = int(item["comment_lines"]) + comment
        item["blank_lines"] = int(item["blank_lines"]) + blank

    rows = [
        FileTypeSummary(
            language=str(values["language"]),
            extension=str(values["extension"]),
            file_type=str(values["file_type"]),
            file_kind=str(values["file_kind"]),
            bucket=str(values["bucket"]),
            files=int(values["files"]),
            total_lines=int(values["total_lines"]),
            code_lines=int(values["code_lines"]),
            comment_lines=int(values["comment_lines"]),
            blank_lines=int(values["blank_lines"]),
            size_bytes=int(values["size_bytes"]),
            mapping_source=str(values["mapping_source"]),
            mapping_pattern=str(values["mapping_pattern"]),
        )
        for values in grouped.values()
    ]
    return sorted(
        rows,
        key=lambda item: (
            -item.code_lines,
            -item.total_lines,
            -item.files,
            item.language.lower(),
        ),
    )


def unmapped_extension_counts(
    files: list[DiscoveryFile],
    *,
    resolver: FileTypeResolver | None = None,
) -> dict[str, int]:
    resolver = resolver or get_default_file_type_resolver()
    counts: dict[str, int] = defaultdict(int)
    for row in files:
        resolved = resolver.resolve(row.path)
        if resolved.mapping_source != MappingSource.UNKNOWN:
            continue
        ext = resolved.extension
        if ext and ext not in {NO_EXTENSION, NO_EXTENSION_FILE_TYPE}:
            counts[ext] += 1
    return dict(counts)
