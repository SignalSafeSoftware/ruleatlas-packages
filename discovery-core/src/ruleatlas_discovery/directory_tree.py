"""Directory tree construction from flat file inventories."""

from __future__ import annotations

from dataclasses import dataclass, field

from ruleatlas_discovery.constants import (
    FILE_NODE_ID_PREFIX,
    NO_EXTENSION,
    UNKNOWN_CLASSIFICATION,
    UNKNOWN_LANGUAGE_KEY,
    BucketHint,
    FileKind,
    NodeKind,
)
from ruleatlas_discovery.models import DirectoryNode, DiscoveryFile


def extension_from_path(path: str) -> str:
    base = path.split("/")[-1] if path else path
    dot = base.rfind(".")
    if dot <= 0:
        return NO_EXTENSION
    return base[dot:]


@dataclass
class _MutableFolder:
    display_path: str
    name: str
    depth: int
    child_folders: dict[str, _MutableFolder] = field(default_factory=dict)
    files: list[DiscoveryFile] = field(default_factory=list)


def _line_value(value: int | None) -> int:
    return value if isinstance(value, int) and value >= 0 else 0


def _folder_key(parent_path: str, name: str) -> str:
    if not parent_path:
        return name
    return f"{parent_path}/{name}"


def _file_to_node(row: DiscoveryFile, *, name: str, depth: int) -> DirectoryNode:
    display_path = row.effective_display_path
    return DirectoryNode(
        id=f"{FILE_NODE_ID_PREFIX}{display_path}",
        kind=NodeKind.FILE,
        name=name,
        display_path=display_path,
        raw_path=row.path,
        depth=depth,
        language=row.language or UNKNOWN_LANGUAGE_KEY,
        extension=extension_from_path(display_path),
        file_kind=row.file_kind or FileKind.UNKNOWN,
        classification=row.classification or UNKNOWN_CLASSIFICATION,
        bucket=row.bucket or BucketHint.UNKNOWN,
        folders_count=0,
        files_count=1,
        size_bytes=int(row.size_bytes or 0),
        code_lines=_line_value(row.code_lines),
        comment_lines=_line_value(row.comment_lines),
        blank_lines=_line_value(row.blank_lines),
        total_lines=int(row.line_count or 0),
        children=[],
    )


def _finalize_folder(folder: _MutableFolder) -> DirectoryNode:
    child_folder_nodes = [_finalize_folder(child) for child in sorted(folder.child_folders.values(), key=lambda item: item.name.lower())]
    file_nodes = [
        _file_to_node(
            row,
            name=row.effective_display_path.split("/")[-1],
            depth=folder.depth + 1,
        )
        for row in folder.files
    ]
    children = sorted(
        [*child_folder_nodes, *file_nodes],
        key=lambda node: (0 if node.kind == NodeKind.FOLDER else 1, node.name.lower()),
    )

    files_count = sum(child.files_count for child in children)
    folders_count = sum(1 for child in children if child.kind == NodeKind.FOLDER)
    size_bytes = sum(child.size_bytes for child in children)
    code_lines = sum(child.code_lines for child in children)
    comment_lines = sum(child.comment_lines for child in children)
    blank_lines = sum(child.blank_lines for child in children)
    total_lines = sum(child.total_lines for child in children)

    return DirectoryNode(
        id=folder.display_path,
        kind=NodeKind.FOLDER,
        name=folder.name,
        display_path=folder.display_path,
        raw_path=folder.display_path,
        depth=folder.depth,
        folders_count=folders_count,
        files_count=files_count,
        size_bytes=size_bytes,
        code_lines=code_lines,
        comment_lines=comment_lines,
        blank_lines=blank_lines,
        total_lines=total_lines,
        children=children,
    )


def build_directory_tree(
    files: list[DiscoveryFile],
    *,
    source_root_prefix: str | None = None,
) -> list[DirectoryNode]:
    """Build a nested directory tree from discovery file rows."""

    def to_display_path(path: str) -> str:
        normalized = path.replace("\\", "/")
        if source_root_prefix:
            prefix = source_root_prefix.rstrip("/") + "/"
            if normalized.startswith(prefix):
                return normalized[len(prefix) :]
            if normalized == source_root_prefix.rstrip("/"):
                return ""
        return normalized

    root_folders: dict[str, _MutableFolder] = {}
    root_files: list[tuple[DiscoveryFile, str, int]] = []

    for row in files:
        display_path = row.effective_display_path
        if source_root_prefix and row.display_path is None:
            display_path = to_display_path(row.path)
        segments = [part for part in display_path.split("/") if part]
        if not segments:
            continue

        if len(segments) == 1:
            root_files.append((row, segments[0], 0))
            continue

        *folder_parts, _file_name = segments
        parent: _MutableFolder | None = None
        current_path = ""
        bucket = root_folders
        for index, folder_name in enumerate(folder_parts):
            current_path = _folder_key(current_path, folder_name)
            if folder_name not in bucket:
                bucket[folder_name] = _MutableFolder(
                    display_path=current_path,
                    name=folder_name,
                    depth=index,
                )
            parent = bucket[folder_name]
            bucket = parent.child_folders
        if parent is not None:
            parent.files.append(row)

    roots = [_finalize_folder(folder) for folder in sorted(root_folders.values(), key=lambda item: item.name.lower())]
    root_file_nodes = [_file_to_node(row, name=name, depth=depth) for row, name, depth in root_files]
    return sorted(
        [*roots, *root_file_nodes],
        key=lambda node: (0 if node.kind == NodeKind.FOLDER else 1, node.name.lower()),
    )
