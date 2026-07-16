"""Global built-in file type mappings and resolver for Discovery."""

from __future__ import annotations

from dataclasses import dataclass

from ruleatlas_contracts.enums import (
    CommentStyle,
    FileKind,
    FileTypeMappingSource,
    FileTypeMatchType,
    ProductionBucketHint,
)

from ruleatlas_discovery import (
    FileTypeMapping as CoreFileTypeMapping,
)
from ruleatlas_discovery import (
    FileTypeResolver as CoreFileTypeResolver,
)
from ruleatlas_discovery import (
    ResolvedFileType as CoreResolvedFileType,
)
from ruleatlas_discovery import (
    reset_default_file_type_resolver as reset_core_default_resolver,
)

UNKNOWN_LANGUAGE = "Unknown"
UNKNOWN_LANGUAGE_KEY = "unknown"


@dataclass(frozen=True)
class FileTypeMappingEntry:
    pattern: str
    match_type: FileTypeMatchType
    language: str
    language_key: str
    display_type: str
    file_kind: FileKind
    default_bucket_hint: ProductionBucketHint
    comment_style: CommentStyle
    is_binary: bool = False
    is_generated_hint: bool = False
    description: str = ""
    enabled: bool = True
    source: FileTypeMappingSource = FileTypeMappingSource.BUILT_IN
    id: str | None = None

    def stable_id(self) -> str:
        if self.id:
            return self.id
        return f"builtin:{self.match_type.value}:{self.pattern}"


@dataclass(frozen=True)
class ResolvedFileType:
    language: str
    language_key: str
    extension: str
    display_type: str
    file_type: str
    file_kind: FileKind
    default_bucket_hint: ProductionBucketHint
    comment_style: CommentStyle
    mapping_source: FileTypeMappingSource
    mapping_pattern: str
    is_binary: bool = False
    is_generated_hint: bool = False


def _enum_value(value: object) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _entry_to_core(entry: FileTypeMappingEntry) -> CoreFileTypeMapping:
    return CoreFileTypeMapping(
        id=entry.id,
        pattern=entry.pattern,
        match_type=_enum_value(entry.match_type),
        language=entry.language,
        language_key=entry.language_key,
        display_type=entry.display_type,
        file_kind=_enum_value(entry.file_kind),
        default_bucket_hint=_enum_value(entry.default_bucket_hint),
        comment_style=_enum_value(entry.comment_style),
        is_binary=entry.is_binary,
        is_generated_hint=entry.is_generated_hint,
        description=entry.description,
        enabled=entry.enabled,
        source=_enum_value(entry.source),
    )


def _entry_from_core(entry: CoreFileTypeMapping) -> FileTypeMappingEntry:
    return FileTypeMappingEntry(
        id=entry.id,
        pattern=entry.pattern,
        match_type=FileTypeMatchType(entry.match_type),
        language=entry.language,
        language_key=entry.language_key,
        display_type=entry.display_type,
        file_kind=FileKind(entry.file_kind),
        default_bucket_hint=ProductionBucketHint(entry.default_bucket_hint),
        comment_style=CommentStyle(entry.comment_style),
        is_binary=entry.is_binary,
        is_generated_hint=entry.is_generated_hint,
        description=entry.description,
        enabled=entry.enabled,
        source=FileTypeMappingSource(entry.source),
    )


def _resolved_from_core(resolved: CoreResolvedFileType) -> ResolvedFileType:
    return ResolvedFileType(
        language=resolved.language,
        language_key=resolved.language_key,
        extension=resolved.extension,
        display_type=resolved.display_type,
        file_type=resolved.file_type,
        file_kind=FileKind(resolved.file_kind),
        default_bucket_hint=ProductionBucketHint(resolved.default_bucket_hint),
        comment_style=CommentStyle(resolved.comment_style),
        mapping_source=FileTypeMappingSource(resolved.mapping_source),
        mapping_pattern=resolved.mapping_pattern,
        is_binary=resolved.is_binary,
        is_generated_hint=resolved.is_generated_hint,
    )


class FileTypeResolver:
    """Resolve file paths using built-in and custom global mappings."""

    def __init__(self, custom_entries: list[FileTypeMappingEntry] | None = None) -> None:
        core_custom = [_entry_to_core(entry) for entry in custom_entries or []]
        self._core = CoreFileTypeResolver(core_custom)

    def resolve(self, path: str) -> ResolvedFileType:
        return _resolved_from_core(self._core.resolve(path))

    def list_entries(self) -> list[FileTypeMappingEntry]:
        return [_entry_from_core(entry) for entry in self._core.list_entries()]


_DEFAULT_RESOLVER: FileTypeResolver | None = None


def get_default_file_type_resolver() -> FileTypeResolver:
    global _DEFAULT_RESOLVER
    if _DEFAULT_RESOLVER is None:
        _DEFAULT_RESOLVER = FileTypeResolver()
    return _DEFAULT_RESOLVER


def reset_default_file_type_resolver() -> None:
    global _DEFAULT_RESOLVER
    _DEFAULT_RESOLVER = None
    reset_core_default_resolver()
