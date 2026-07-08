"""Typed DTOs for discovery inventory and metrics."""

from __future__ import annotations

from dataclasses import dataclass, field

from ruleatlas_discovery.constants import (
    BUILTIN_ID_PREFIX,
    NO_EXTENSION,
    UNKNOWN_CLASSIFICATION,
    UNKNOWN_LANGUAGE_KEY,
    BucketHint,
    FileKind,
    MappingSource,
)


@dataclass(frozen=True)
class FileTypeMapping:
    pattern: str
    match_type: str
    language: str
    language_key: str
    display_type: str
    file_kind: str
    default_bucket_hint: str
    comment_style: str
    # Canonical extension this mapping reports, regardless of the on-disk
    # suffix. Lets a single mapping fold variant suffixes (e.g. `*.y*ml`
    # matching both `.yml` and `.yaml`) into one bucket without hardcoding
    # extensions in the resolver. `None` means "use the file's own suffix".
    normalized_extension: str | None = None
    is_binary: bool = False
    is_generated_hint: bool = False
    description: str = ""
    enabled: bool = True
    source: str = MappingSource.BUILT_IN
    id: str | None = None

    def stable_id(self) -> str:
        if self.id:
            return self.id
        return f"{BUILTIN_ID_PREFIX}:{self.match_type}:{self.pattern}"


@dataclass(frozen=True)
class ResolvedFileType:
    language: str
    language_key: str
    extension: str
    display_type: str
    file_type: str
    file_kind: str
    default_bucket_hint: str
    comment_style: str
    mapping_source: str
    mapping_pattern: str
    is_binary: bool = False
    is_generated_hint: bool = False


@dataclass(frozen=True)
class DiscoveryFile:
    path: str
    display_path: str | None = None
    language: str | None = None
    extension: str | None = None
    file_kind: str | None = None
    classification: str | None = None
    bucket: str | None = None
    size_bytes: int = 0
    line_count: int = 0
    code_lines: int | None = None
    comment_lines: int | None = None
    blank_lines: int | None = None
    file_id: str | None = None

    @property
    def effective_display_path(self) -> str:
        return self.display_path or self.path


@dataclass(frozen=True)
class DiscoveryScope:
    include_globs: list[str] = field(default_factory=list)
    exclude_globs: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class LineCountSummary:
    total_lines: int
    code_lines: int
    comment_lines: int
    blank_lines: int
    files: int = 0


@dataclass(frozen=True)
class FileTypeSummary:
    language: str
    extension: str
    file_type: str
    file_kind: str
    bucket: str
    files: int
    total_lines: int
    code_lines: int
    comment_lines: int
    blank_lines: int
    size_bytes: int = 0
    mapping_source: str = MappingSource.UNKNOWN
    mapping_pattern: str = ""


@dataclass
class DirectoryNode:
    id: str
    kind: str
    name: str
    display_path: str
    raw_path: str
    depth: int
    language: str = UNKNOWN_LANGUAGE_KEY
    extension: str = NO_EXTENSION
    file_kind: str = FileKind.UNKNOWN
    classification: str = UNKNOWN_CLASSIFICATION
    bucket: str = BucketHint.UNKNOWN
    folders_count: int = 0
    files_count: int = 0
    size_bytes: int = 0
    code_lines: int = 0
    comment_lines: int = 0
    blank_lines: int = 0
    total_lines: int = 0
    children: list[DirectoryNode] = field(default_factory=list)


@dataclass
class InventoryMetrics:
    total_files: int
    total_lines: int
    code_lines: int
    comment_lines: int
    blank_lines: int
    by_file_type: list[FileTypeSummary] = field(default_factory=list)
