#!/usr/bin/env python3
"""Validate a package-specific release tag against the package version."""

from __future__ import annotations

import argparse
import ast
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


def package_version(path: Path) -> str:
    module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in module.body:
        if (
            isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "__version__" for target in node.targets)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            return node.value.value
    raise SystemExit(f"{path}: __version__ string was not found")


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
        with args.github_output.open("a", encoding="utf-8") as output:
            output.write(f"package={package}\nversion={source_version}\n")
    print(f"{package} release tag matches version {source_version}")


if __name__ == "__main__":
    main()
