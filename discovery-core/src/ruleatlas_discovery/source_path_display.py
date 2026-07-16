"""Display-path normalization for discovery inventory (read-time only; raw paths unchanged)."""

from __future__ import annotations

from collections import Counter

# Top-level segments that usually indicate real repo layout, not a ZIP wrapper folder.
_COMMON_CODE_ROOTS = frozenset(
    {
        "backend",
        "frontend",
        "src",
        "lib",
        "apps",
        "app",
        "docs",
        "doc",
        "tests",
        "test",
        "pkg",
        "internal",
        "api",
        "web",
        "server",
        "client",
        "services",
        "modules",
        "packages",
        "cmd",
        "tools",
        "scripts",
    }
)


ROOT_SEGMENT = "(root)"


def normalize_path(path: str) -> str:
    return path.replace("\\", "/").strip("/")


def infer_source_root_prefix(paths: list[str], *, min_coverage: float = 0.85) -> str | None:
    """Infer a redundant archive/repo wrapper prefix shared by most paths."""
    if not paths:
        return None

    normalized = [normalize_path(path) for path in paths if path]
    if not normalized:
        return None

    under_prefix: Counter[str] = Counter()
    first_segments: Counter[str] = Counter()
    for path in normalized:
        if "/" not in path:
            first_segments[ROOT_SEGMENT] += 1
            continue
        segment = path.split("/", 1)[0]
        first_segments[segment] += 1
        under_prefix[segment] += 1

    total = len(normalized)
    candidates: list[tuple[str, float, int]] = []
    for segment, count in under_prefix.items():
        coverage = count / total
        if coverage >= min_coverage:
            candidates.append((segment, coverage, count))

    if not candidates:
        return None

    candidates.sort(key=lambda item: (-item[1], -item[2], item[0]))
    best_segment, _, _ = candidates[0]

    other_significant_roots = sum(
        1
        for segment, count in first_segments.items()
        if segment not in {best_segment, ROOT_SEGMENT} and count >= max(2, int(total * 0.05))
    )
    if best_segment.lower() in _COMMON_CODE_ROOTS and other_significant_roots >= 1:
        return None

    if len(candidates) >= 2 and candidates[1][1] >= min_coverage * 0.5:
        return None

    return best_segment


def to_display_path(raw_path: str, prefix: str | None) -> str:
    if not prefix:
        return raw_path
    normalized = normalize_path(raw_path)
    needle = f"{prefix}/"
    if normalized.startswith(needle):
        return normalized[len(needle) :]
    return raw_path


def to_raw_path(display_path: str, prefix: str | None) -> str:
    if not prefix:
        return display_path
    normalized = normalize_path(display_path)
    if normalized.startswith(f"{prefix}/"):
        return normalized
    return f"{prefix}/{normalized}"


def top_directory_for_display_path(display_path: str) -> str:
    normalized = normalize_path(display_path)
    if not normalized or "/" not in normalized:
        return ROOT_SEGMENT
    return normalized.split("/", 1)[0]


def folder_paths_for_display_path(display_path: str) -> list[str]:
    """All distinct parent directory paths for a file (display path)."""
    normalized = normalize_path(display_path)
    if not normalized or "/" not in normalized:
        return []
    parts = normalized.split("/")[:-1]
    return ["/".join(parts[: index + 1]) for index in range(len(parts))]


def count_distinct_folders(display_paths: list[str]) -> int:
    folders: set[str] = set()
    for display_path in display_paths:
        folders.update(folder_paths_for_display_path(display_path))
    return len(folders)


def nested_folder_count_under_top(display_paths: list[str], top_directory: str) -> int:
    """Distinct nested folder paths under a top-level directory (excludes the top dir itself)."""
    if top_directory == ROOT_SEGMENT:
        return 0
    prefix = f"{top_directory}/"
    nested: set[str] = set()
    for display_path in display_paths:
        for folder in folder_paths_for_display_path(display_path):
            if folder.startswith(prefix):
                nested.add(folder)
    return len(nested)


def compute_top_directories_by_line_count(
    file_rows: list[dict],
    prefix: str | None,
    *,
    limit: int = 20,
) -> list[dict[str, str | int]]:
    lines_by_directory: Counter[str] = Counter()
    for row in file_rows:
        raw_path = str(row.get("path") or "")
        display_path = str(row.get("display_path") or to_display_path(raw_path, prefix))
        raw_line_count = row.get("line_count")
        line_count = raw_line_count if isinstance(raw_line_count, (int, float, str, bytes, bytearray)) else 0
        lines_by_directory[top_directory_for_display_path(display_path)] += int(line_count or 0)
    rows: list[dict[str, str | int]] = [
        {"directory": directory, "line_count": count} for directory, count in lines_by_directory.items()
    ]
    return sorted(
        rows,
        key=lambda item: int(item["line_count"]),
        reverse=True,
    )[:limit]


def compute_top_files_by_rule_count(
    rules_by_raw_path: dict[str, int],
    prefix: str | None,
    *,
    limit: int = 20,
) -> list[dict[str, str | int]]:
    rows: list[dict[str, str | int]] = sorted(
        (
            {
                "path": to_display_path(path, prefix),
                "raw_path": path,
                "rule_count": count,
            }
            for path, count in rules_by_raw_path.items()
        ),
        key=lambda item: int(item["rule_count"]),
        reverse=True,
    )
    return rows[:limit]


def enrich_discovery_file_rows(file_rows: list[dict]) -> tuple[str | None, list[dict]]:
    prefix = infer_source_root_prefix([str(row.get("path") or "") for row in file_rows])
    for row in file_rows:
        raw_path = str(row.get("path") or "")
        row["display_path"] = to_display_path(raw_path, prefix)
    return prefix, file_rows


def apply_display_paths(paths: list[str]) -> tuple[str | None, list[str]]:
    prefix = infer_source_root_prefix(paths)
    return prefix, [to_display_path(path, prefix) for path in paths]


def resolve_project_file_path(file_path: str, known_paths: list[str]) -> str:
    """Map a user-facing display path back to the stored raw path when unambiguous."""
    if file_path in known_paths:
        return file_path
    prefix = infer_source_root_prefix(known_paths)
    if prefix:
        candidate = to_raw_path(file_path, prefix)
        if candidate in known_paths:
            return candidate
    normalized = normalize_path(file_path)
    matches = [
        path
        for path in known_paths
        if path == file_path or normalize_path(path).endswith(f"/{normalized}") or normalize_path(path) == normalized
    ]
    if len(matches) == 1:
        return matches[0]
    return file_path
