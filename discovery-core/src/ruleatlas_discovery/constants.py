"""Shared enums and sentinel constants for discovery core.

These values are the domain vocabulary used across file-type mapping,
line-count aggregation, and directory-tree construction. They are defined
once here so the rest of the package (and downstream consumers) can rely on
typed members instead of scattered string literals.

The enums subclass :class:`enum.StrEnum`, so every member is also a plain
``str``. That keeps them backward compatible with data that arrives as raw
strings (e.g. deserialized JSON or database rows): ``FileKind.CONFIG == "config"``
is always ``True``.
"""

from __future__ import annotations

from enum import StrEnum


class MatchType(StrEnum):
    """How a :class:`FileTypeMapping` pattern is matched against a path."""

    FILENAME = "filename"
    GLOB = "glob"
    EXTENSION = "extension"


class FileKind(StrEnum):
    """High-level intent of a file, independent of its language/extension."""

    CODE = "code"
    TEST = "test"
    DOCUMENTATION = "documentation"
    CONFIG = "config"
    DATA = "data"
    SCRIPT = "script"
    BUILD = "build"
    ARTIFACT = "artifact"
    GENERATED = "generated"
    UNKNOWN = "unknown"


class BucketHint(StrEnum):
    """Default bucket a file falls into for reporting/rollups."""

    PRODUCTION = "production"
    TESTS = "tests"
    DOCS = "docs"
    CONFIG = "config"
    GENERATED_VENDOR = "generated_vendor"
    ARTIFACTS = "artifacts"
    UNKNOWN = "unknown"


class CommentStyle(StrEnum):
    """Comment syntax family used when counting comment lines."""

    SLASH = "slash"
    HASH = "hash"
    YAML = "yaml"
    SQL = "sql"
    HTML = "html"
    NONE = "none"
    UNSUPPORTED = "unsupported"


class MappingSource(StrEnum):
    """Origin of a resolved file-type mapping."""

    BUILT_IN = "built_in"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


class NodeKind(StrEnum):
    """Kind of node in a directory tree."""

    FOLDER = "folder"
    FILE = "file"


# Language sentinels -------------------------------------------------------
UNKNOWN_LANGUAGE = "Unknown"
UNKNOWN_LANGUAGE_KEY = "unknown"
UNKNOWN_CLASSIFICATION = "unknown"

# Extension / file-type sentinels -----------------------------------------
NO_EXTENSION = "(none)"
NO_EXTENSION_FILE_TYPE = "no_extension"

# Misc ---------------------------------------------------------------------
EMPTY_PATTERN = ""
BUILTIN_ID_PREFIX = "builtin"
FILE_NODE_ID_PREFIX = "file:"
