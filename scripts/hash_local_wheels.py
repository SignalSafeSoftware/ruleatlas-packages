#!/usr/bin/env python3
"""Write a hashed requirements file for local wheel artifacts."""

from __future__ import annotations

import argparse
import hashlib
import os
import tempfile
from pathlib import Path


def _trusted_roots() -> list[Path]:
    roots = [Path.cwd().resolve(), Path(tempfile.gettempdir()).resolve()]
    runner_temp = os.environ.get("RUNNER_TEMP")
    if runner_temp:
        roots.append(Path(runner_temp).expanduser().resolve())
    return roots


def _resolve_trusted(path: Path) -> Path:
    candidate = path.expanduser()
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    resolved = candidate.resolve()
    if not any(resolved == root or resolved.is_relative_to(root) for root in _trusted_roots()):
        raise SystemExit(f"{path}: path is outside trusted directories")
    return resolved


def hashed_requirement(wheel: Path) -> str:
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    return f"{wheel.resolve().as_uri()} --hash=sha256:{digest}\n"


def write_hashed_requirements(wheel_dir: Path, output: Path) -> None:
    wheels = sorted(wheel_dir.glob("*.whl"))
    if not wheels:
        raise SystemExit(f"no wheels found in {wheel_dir}")
    output.write_text("".join(hashed_requirement(wheel) for wheel in wheels), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("wheel_dir", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    args = parser.parse_args()
    wheel_dir = _resolve_trusted(args.wheel_dir)
    output = _resolve_trusted(args.output)
    if not wheel_dir.is_dir():
        raise SystemExit(f"{wheel_dir}: not a directory")
    write_hashed_requirements(wheel_dir, output)


if __name__ == "__main__":
    main()
