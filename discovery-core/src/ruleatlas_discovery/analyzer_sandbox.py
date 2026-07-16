"""Analyzer sandbox guards for untrusted repository workspaces."""

from __future__ import annotations

import hashlib
import os
import re
import resource
from dataclasses import dataclass
from pathlib import Path

SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"]?[^\s'\"]{8,}"),
    re.compile(r"(?i)BEGIN (RSA |OPENSSH )?PRIVATE KEY"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
)

DEFAULT_MAX_FILE_BYTES = 25 * 1024 * 1024
DEFAULT_MAX_TOTAL_BYTES = 500 * 1024 * 1024
DEFAULT_MAX_FILES = 50_000
DEFAULT_MAX_DEPTH = 40
DEFAULT_CPU_SECONDS = 120
DEFAULT_AS_BYTES = 2 * 1024 * 1024 * 1024  # 2 GiB soft address-space hint


class SandboxViolation(Exception):
    """Raised when a workspace path or archive violates sandbox policy."""


@dataclass(frozen=True)
class SandboxLimits:
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES
    max_files: int = DEFAULT_MAX_FILES
    max_depth: int = DEFAULT_MAX_DEPTH
    cpu_seconds: int = DEFAULT_CPU_SECONDS
    address_space_bytes: int = DEFAULT_AS_BYTES
    allow_network: bool = False


def resolve_under_root(root: Path, relative: str | Path) -> Path:
    """Resolve a path under root; reject traversal and absolute escapes."""
    root = root.resolve()
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise SandboxViolation(f"Path escapes workspace: {relative}") from exc
    return candidate


def assert_not_symlink(path: Path) -> None:
    if path.is_symlink():
        raise SandboxViolation(f"Symlinks are not allowed: {path}")


def redact_secrets(text: str) -> tuple[str, int]:
    count = 0
    out = text
    for pattern in SECRET_PATTERNS:
        out, n = pattern.subn("[REDACTED]", out)
        count += n
    return out, count


def apply_process_limits(limits: SandboxLimits | None = None) -> dict:
    """Best-effort RLIMIT caps (no-op where unsupported, e.g. some macOS limits)."""
    limits = limits or SandboxLimits()
    applied: dict[str, str] = {}
    if not hasattr(resource, "setrlimit"):
        return {"status": "unsupported"}
    try:
        resource.setrlimit(resource.RLIMIT_CPU, (limits.cpu_seconds, limits.cpu_seconds))
        applied["cpu_seconds"] = str(limits.cpu_seconds)
    except (ValueError, OSError) as exc:
        applied["cpu_error"] = str(exc)
    try:
        _, hard = resource.getrlimit(resource.RLIMIT_AS)
        target = min(limits.address_space_bytes, hard if hard > 0 else limits.address_space_bytes)
        resource.setrlimit(resource.RLIMIT_AS, (target, hard if hard > 0 else target))
        applied["address_space_bytes"] = str(target)
    except (ValueError, OSError, AttributeError) as exc:
        applied["as_error"] = str(exc)
    applied["network_egress"] = "restricted" if not limits.allow_network else "allowed"
    applied["unprivileged"] = str(os.geteuid() != 0) if hasattr(os, "geteuid") else "unknown"
    return applied


def scan_workspace(
    root: Path,
    *,
    limits: SandboxLimits | None = None,
) -> dict:
    """Walk workspace enforcing size/depth/symlink/traversal guards; redact secrets in text samples."""
    limits = limits or SandboxLimits()
    root = root.resolve()
    if not root.is_dir():
        raise SandboxViolation(f"Workspace root is not a directory: {root}")

    total_bytes = 0
    file_count = 0
    redactions = 0
    violations: list[str] = []

    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        rel_dir = Path(dirpath).relative_to(root)
        depth = len(rel_dir.parts)
        if depth > limits.max_depth:
            violations.append(f"max depth exceeded at {rel_dir}")
            dirnames.clear()
            continue
        # Block symlink dirs
        for name in list(dirnames):
            p = Path(dirpath) / name
            if p.is_symlink():
                violations.append(f"symlink directory blocked: {p.relative_to(root)}")
                dirnames.remove(name)
        for name in filenames:
            path = Path(dirpath) / name
            if path.is_symlink():
                violations.append(f"symlink file blocked: {path.relative_to(root)}")
                continue
            try:
                size = path.stat().st_size
            except OSError as exc:
                violations.append(f"stat failed: {path.relative_to(root)} ({exc})")
                continue
            if size > limits.max_file_bytes:
                violations.append(f"file too large: {path.relative_to(root)} ({size} bytes)")
                continue
            total_bytes += size
            file_count += 1
            if file_count > limits.max_files:
                raise SandboxViolation("max file count exceeded")
            if total_bytes > limits.max_total_bytes:
                raise SandboxViolation("max total bytes exceeded (archive bomb / oversized tree)")
            if path.suffix.lower() in {".py", ".ts", ".js", ".cs", ".php", ".env", ".json", ".yml", ".yaml", ".txt"}:
                try:
                    sample = path.read_text(encoding="utf-8", errors="ignore")[:50_000]
                    _, n = redact_secrets(sample)
                    redactions += n
                except OSError:
                    pass

    if violations:
        raise SandboxViolation("; ".join(violations[:20]))

    return {
        "files": file_count,
        "total_bytes": total_bytes,
        "secrets_redacted_samples": redactions,
        "root": str(root),
        "read_only_mount_recommended": True,
        "network_egress": False,
    }


def zip_bomb_guard(uncompressed_bytes: int, compressed_bytes: int, *, max_ratio: float = 100.0) -> None:
    if compressed_bytes <= 0:
        raise SandboxViolation("invalid compressed size")
    ratio = uncompressed_bytes / compressed_bytes
    if ratio > max_ratio or uncompressed_bytes > DEFAULT_MAX_TOTAL_BYTES:
        raise SandboxViolation(
            f"archive bomb suspected: ratio={ratio:.1f}, uncompressed={uncompressed_bytes}"
        )


def content_checksum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
