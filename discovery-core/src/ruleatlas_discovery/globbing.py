"""Include/exclude glob matching for discovery scope."""

from __future__ import annotations

from fnmatch import fnmatch

from ruleatlas_discovery.models import DiscoveryFile, DiscoveryScope


def _pattern_matches_path(normalized: str, pattern: str) -> bool:
    pattern = pattern.replace("\\", "/")
    if fnmatch(normalized, pattern):
        return True
    if pattern.startswith("**/"):
        tail = pattern[3:]
        if not tail:
            return True
        if fnmatch(normalized, tail):
            return True
        if normalized == tail or normalized.endswith(f"/{tail}"):
            return True
    return False


def matches_any_glob(path: str, globs: list[str]) -> bool:
    normalized = path.replace("\\", "/")
    return any(_pattern_matches_path(normalized, pattern) for pattern in globs)


def should_include_path(
    path: str,
    include_globs: list[str],
    exclude_globs: list[str],
) -> bool:
    if exclude_globs and matches_any_glob(path, exclude_globs):
        return False
    if not include_globs:
        return True
    return matches_any_glob(path, include_globs)


def apply_discovery_scope(files: list[DiscoveryFile], scope: DiscoveryScope) -> list[DiscoveryFile]:
    return [row for row in files if should_include_path(row.path, scope.include_globs, scope.exclude_globs)]
