#!/usr/bin/env python3
"""Validate a package-specific release tag against the package version."""

from __future__ import annotations

import argparse
import ast
import os
import re
from pathlib import Path

PACKAGES = {
    "contracts": Path("contracts/src/ruleatlas_contracts/version.py"),
    "persistence": Path("persistence/src/ruleatlas_persistence/version.py"),
    "discovery-core": Path("discovery-core/src/ruleatlas_discovery/version.py"),
    "claims": Path("claims/src/ruleatlas_claims/version.py"),
    "extraction": Path("extraction/src/ruleatlas_extraction/version.py"),
    "exports": Path("exports/src/ruleatlas_exports/version.py"),
    "ai": Path("ai/src/ruleatlas_ai/version.py"),
    "demo": Path("demo/src/ruleatlas_demo/version.py"),
}
TAG_PATTERN = re.compile(r"^(?P<package>[a-z-]+)-v(?P<version>\d+\.\d+\.\d+)$")


def _resolve_under_root(path: Path, root: Path) -> Path:
    candidate = path.expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root):
        raise SystemExit(f"{path}: path is outside the working directory")
    return resolved


def package_version(path: Path, *, cwd: Path | None = None) -> str:
    root = (cwd or Path.cwd()).resolve()
    resolved = _resolve_under_root(path, root)
    module = ast.parse(resolved.read_text(encoding="utf-8"), filename=str(resolved))
    for node in module.body:
        if (
            isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "__version__" for target in node.targets)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            return node.value.value
    raise SystemExit(f"{path}: __version__ string was not found")


def validated_github_output_path(
    path: Path,
    *,
    cwd: Path | None = None,
    github_output: str | None = None,
) -> Path:
    """Resolve *path* and reject writes outside the trusted GitHub output file or cwd."""
    root = (cwd or Path.cwd()).resolve()
    expected = os.environ["GITHUB_OUTPUT"] if github_output is None and "GITHUB_OUTPUT" in os.environ else github_output
    if expected:
        allowed = Path(expected).expanduser()
        if not allowed.is_absolute():
            allowed = root / allowed
        allowed = allowed.resolve()
        resolved = path.expanduser()
        if not resolved.is_absolute():
            resolved = root / resolved
        resolved = resolved.resolve()
        if resolved != allowed:
            raise SystemExit("github-output path does not match GITHUB_OUTPUT")
        return resolved
    return _resolve_under_root(path, root)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("tag", help="Package-specific tag, for example contracts-v0.1.0")
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()

    match = TAG_PATTERN.fullmatch(args.tag)
    if match is None or match["package"] not in PACKAGES:
        choices = ", ".join(f"{name}-v<version>" for name in PACKAGES)
        raise SystemExit(f"invalid release tag {args.tag!r}; expected one of: {choices}")

    package = match["package"]
    tag_version = match["version"]
    source_version = package_version(PACKAGES[package])
    if tag_version != source_version:
        raise SystemExit(
            f"{args.tag}: tag version {tag_version} does not match {package} version {source_version}"
        )

    if args.github_output:
        output_path = validated_github_output_path(args.github_output)
        with output_path.open("a", encoding="utf-8") as output:
            output.write(f"package={package}\nversion={source_version}\n")
    print(f"{package} release tag matches version {source_version}")


if __name__ == "__main__":
    main()
