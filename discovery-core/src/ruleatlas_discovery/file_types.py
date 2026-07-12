"""File type mapping resolution."""

from __future__ import annotations

import fnmatch
from pathlib import Path

from ruleatlas_discovery.builtin_mappings import built_in_file_type_mappings
from ruleatlas_discovery.constants import (
    NO_EXTENSION,
    NO_EXTENSION_FILE_TYPE,
    UNKNOWN_LANGUAGE,
    UNKNOWN_LANGUAGE_KEY,
    BucketHint,
    CommentStyle,
    FileKind,
    MappingSource,
    MatchType,
)
from ruleatlas_discovery.models import FileTypeMapping, ResolvedFileType


def classify_file_type(path: str, resolver: FileTypeResolver | None = None) -> ResolvedFileType:
    return (resolver or get_default_file_type_resolver()).resolve(path)


def _special_glob_matches(pattern: str, path: str, basename: str) -> bool:
    before, after = pattern.split("(.*)", 1)
    glob_stem = before if before.endswith("*") else f"{before}*"
    fn_pattern = f"{glob_stem}{after}"
    root = before[:-1] if before.endswith("*") else before
    exact = f"{root}{after}"
    candidates = (
        (basename, fn_pattern),
        (basename.lower(), fn_pattern.lower()),
        (path, fn_pattern),
        (path.lower(), fn_pattern.lower()),
    )
    for name, fn in candidates:
        if not fnmatch.fnmatch(name, fn):
            continue
        if name == exact or name.lower() == exact.lower():
            return True
        if (name.startswith(f"{root}.") or name.lower().startswith(f"{root.lower()}.")) and (
            not after or name.endswith(after) or name.lower().endswith(after.lower())
        ):
            return True
    return False


def _glob_matches(pattern: str, path: str, basename: str) -> bool:
    if "(.*)" in pattern:
        return _special_glob_matches(pattern, path, basename)
    if fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(basename, pattern):
        return True
    lower_pattern = pattern.lower()
    return fnmatch.fnmatch(path.lower(), lower_pattern) or fnmatch.fnmatch(basename.lower(), lower_pattern)


def _match_score(entry: FileTypeMapping, path: str, basename: str, suffix: str) -> int | None:
    if not entry.enabled:
        return None
    pattern = entry.pattern
    if entry.match_type == MatchType.FILENAME:
        if basename.lower() != pattern.lower():
            return None
        return 10_000 + len(pattern)
    if entry.match_type == MatchType.GLOB:
        if not _glob_matches(pattern, path, basename):
            return None
        return 5_000 + len(pattern)
    if entry.match_type == MatchType.EXTENSION:
        if suffix != pattern.lower():
            return None
        return 1_000 + len(pattern)
    return None


def _entry_to_resolved(entry: FileTypeMapping, path: str) -> ResolvedFileType:
    file_path = Path(path.replace("\\", "/"))
    suffix = file_path.suffix.lower()
    if entry.match_type == MatchType.FILENAME or not suffix:
        extension = NO_EXTENSION
        file_type = entry.display_type
    else:
        extension = entry.normalized_extension or suffix
        # Glob mappings group by semantic display_type (Docker Compose, YAML, etc.).
        # normalized_extension only consolidates the extension column (.yml -> .yaml).
        if entry.match_type == MatchType.GLOB:
            file_type = entry.display_type
        elif entry.normalized_extension and entry.normalized_extension != NO_EXTENSION:
            file_type = entry.normalized_extension
        elif entry.display_type.startswith("."):
            file_type = entry.display_type
        else:
            file_type = suffix
    return ResolvedFileType(
        language=entry.language,
        language_key=entry.language_key,
        extension=extension,
        display_type=entry.display_type,
        file_type=file_type,
        file_kind=entry.file_kind,
        default_bucket_hint=entry.default_bucket_hint,
        comment_style=entry.comment_style,
        mapping_source=entry.source,
        mapping_pattern=entry.pattern,
        is_binary=entry.is_binary,
        is_generated_hint=entry.is_generated_hint,
    )


def _has_concrete_language(entry: FileTypeMapping) -> bool:
    """True when the mapping owns a real language/format, not a role pseudo-label."""
    key = (entry.language_key or "").strip().lower()
    return bool(key) and key != UNKNOWN_LANGUAGE_KEY


def _compose_role_with_language(
    role_resolved: ResolvedFileType,
    language_resolved: ResolvedFileType,
) -> ResolvedFileType:
    """Keep path/role fields from the winning match; keep language from a concrete mapping.

    Path-based role overlays (e.g. ``**/generated/**``) must not erase the
    language/format detected from the file extension.
    """
    comment_style = language_resolved.comment_style
    if comment_style == CommentStyle.UNSUPPORTED:
        comment_style = role_resolved.comment_style
    extension = language_resolved.extension
    if extension == NO_EXTENSION:
        extension = role_resolved.extension
    return ResolvedFileType(
        language=language_resolved.language,
        language_key=language_resolved.language_key,
        extension=extension,
        display_type=role_resolved.display_type,
        file_type=role_resolved.file_type,
        file_kind=role_resolved.file_kind,
        default_bucket_hint=role_resolved.default_bucket_hint,
        comment_style=comment_style,
        mapping_source=role_resolved.mapping_source,
        mapping_pattern=role_resolved.mapping_pattern,
        is_binary=role_resolved.is_binary or language_resolved.is_binary,
        is_generated_hint=role_resolved.is_generated_hint or language_resolved.is_generated_hint,
    )


def unknown_resolved_file_type(path: str) -> ResolvedFileType:
    file_path = Path(path.replace("\\", "/"))
    suffix = file_path.suffix.lower()
    extension = suffix if suffix else NO_EXTENSION
    file_type = suffix if suffix else NO_EXTENSION_FILE_TYPE
    return ResolvedFileType(
        language=UNKNOWN_LANGUAGE,
        language_key=UNKNOWN_LANGUAGE_KEY,
        extension=extension,
        display_type=file_type,
        file_type=file_type,
        file_kind=FileKind.UNKNOWN,
        default_bucket_hint=BucketHint.UNKNOWN,
        comment_style=CommentStyle.UNSUPPORTED,
        mapping_source=MappingSource.UNKNOWN,
        mapping_pattern="",
    )


class FileTypeResolver:
    """Resolve file paths using built-in and custom global mappings."""

    def __init__(self, custom_entries: list[FileTypeMapping] | None = None) -> None:
        merged: dict[tuple[str, str], FileTypeMapping] = {}
        for entry in built_in_file_type_mappings():
            merged[(entry.match_type, entry.pattern.lower())] = entry
        for entry in custom_entries or []:
            if not entry.enabled:
                merged.pop((entry.match_type, entry.pattern.lower()), None)
                continue
            merged[(entry.match_type, entry.pattern.lower())] = entry
        self._entries = list(merged.values())

    def resolve(self, path: str) -> ResolvedFileType:
        normalized = path.replace("\\", "/")
        basename = Path(normalized).name
        suffix = Path(normalized).suffix.lower()
        scored: list[tuple[int, FileTypeMapping]] = []
        for entry in self._entries:
            score = _match_score(entry, normalized, basename, suffix)
            if score is None:
                continue
            if entry.source == MappingSource.CUSTOM:
                score += 50_000
            scored.append((score, entry))
        if not scored:
            return unknown_resolved_file_type(path)
        scored.sort(key=lambda item: item[0], reverse=True)
        best_entry = scored[0][1]
        role_resolved = _entry_to_resolved(best_entry, path)
        if _has_concrete_language(best_entry):
            return role_resolved
        for _, candidate in scored[1:]:
            if _has_concrete_language(candidate):
                return _compose_role_with_language(role_resolved, _entry_to_resolved(candidate, path))
        return role_resolved

    def list_entries(self) -> list[FileTypeMapping]:
        return list(self._entries)


_DEFAULT_RESOLVER: FileTypeResolver | None = None


def get_default_file_type_resolver() -> FileTypeResolver:
    global _DEFAULT_RESOLVER
    if _DEFAULT_RESOLVER is None:
        _DEFAULT_RESOLVER = FileTypeResolver()
    return _DEFAULT_RESOLVER


def reset_default_file_type_resolver() -> None:
    global _DEFAULT_RESOLVER
    _DEFAULT_RESOLVER = None
