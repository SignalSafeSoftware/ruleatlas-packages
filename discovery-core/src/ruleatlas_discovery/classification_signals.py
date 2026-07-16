"""Explicit classification rules and explainability signals for discovery inventory."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from pathlib import Path

from ruleatlas_contracts.enums import SourceFileClassification, SourceType

OPS_ONLY_FILENAMES: frozenset[str] = frozenset(
    {
        "dockerfile",
        "makefile",
        "gnumakefile",
        "cmakelists.txt",
        "docker-compose.yml",
        "docker-compose.yaml",
        "nginx.conf",
        ".dockerignore",
        ".editorconfig",
        ".npmrc",
        ".prettierignore",
        ".eslintignore",
        ".gitignore",
        ".pre-commit-config.yaml",
        ".pre-commit-config.yml",
        ".localstack",
        ".ebcli",
        ".sonar-report-task-path",
        "procfile",
        "jenkinsfile",
        "vagrantfile",
        "codeowners",
        "pyproject.toml",
        "poetry.lock",
        "package.json",
        "tsconfig.json",
        "vite.config.ts",
        "eslint.config.ts",
        "vitest.config.ts",
    }
)

OPS_ONLY_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".conf",
        ".cfg",
        ".ini",
        ".properties",
        ".toml",
        ".yaml",
        ".yml",
        ".json",
        ".env",
        ".example",
        ".production",
        ".localstack",
        ".ebcli",
        ".poetry",
        ".pyl",
        ".in",
    }
)

DOCUMENTATION_FILENAMES: frozenset[str] = frozenset(
    {
        "readme",
        "license",
        "licence",
        "notice",
    }
)

GENERATED_ARTIFACT_FILENAMES: frozenset[str] = frozenset(
    {
        "coverage.xml",
        "coverage.json",
        "junit.xml",
        "lcov.info",
        ".coverage",
        ".sonar-report-task-path",
    }
)

GENERATED_ARTIFACT_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".log",
        ".out",
        ".output",
        ".coverage",
    }
)

OPS_PATH_PARTS: frozenset[str] = frozenset(
    {
        "infra",
        "terraform",
        "helm",
        "k8s",
        "docker",
        ".github",
        "deploy",
        "deployment",
        "ops",
    }
)


@dataclass(frozen=True)
class ClassificationExplanation:
    classification: SourceFileClassification
    signal: str
    detail: str


def _normalized(path: Path) -> tuple[str, str, frozenset[str]]:
    normalized = str(path).replace("\\", "/")
    name = path.name.lower()
    parts = frozenset(part.lower() for part in path.parts)
    return normalized, name, parts


def _match_env_file(name: str) -> bool:
    return name.startswith(".env.") or name == ".env"


def _match_dockerfile_variant(name: str) -> bool:
    return name == "dockerfile" or name.startswith("dockerfile.")


def _explanation(
    classification: SourceFileClassification,
    signal: str,
    detail: str,
) -> ClassificationExplanation:
    return ClassificationExplanation(classification=classification, signal=signal, detail=detail)


def _match_filename_signals(name: str, suffix: str, *, display_name: str) -> ClassificationExplanation | None:
    if name in GENERATED_ARTIFACT_FILENAMES:
        return _explanation(SourceFileClassification.GENERATED_VENDOR, "exact_filename", name)
    if suffix in GENERATED_ARTIFACT_EXTENSIONS:
        return _explanation(SourceFileClassification.GENERATED_VENDOR, "extension", suffix)
    if _match_dockerfile_variant(name):
        return _explanation(SourceFileClassification.OPS_ONLY, "exact_filename", display_name)
    if name in OPS_ONLY_FILENAMES:
        return _explanation(SourceFileClassification.OPS_ONLY, "exact_filename", name)
    if _match_env_file(name):
        return _explanation(SourceFileClassification.OPS_ONLY, "exact_filename", name)
    if name in DOCUMENTATION_FILENAMES or (suffix in {".md", ".rst", ".txt"} and name.startswith("readme")):
        return _explanation(SourceFileClassification.DOCUMENTATION_EVIDENCE, "exact_filename", name)
    return None


def _match_path_signals(parts: frozenset[str], suffix: str) -> ClassificationExplanation | None:
    if ".github" in parts:
        return _explanation(SourceFileClassification.OPS_ONLY, "path_rule", ".github/**")
    if any(part in OPS_PATH_PARTS for part in parts):
        detail = next(part for part in OPS_PATH_PARTS if part in parts)
        return _explanation(SourceFileClassification.OPS_ONLY, "path_rule", detail)
    if suffix in OPS_ONLY_EXTENSIONS:
        return _explanation(SourceFileClassification.OPS_ONLY, "extension", suffix)
    return None


def _match_test_glob(name: str) -> ClassificationExplanation | None:
    if any(fnmatch.fnmatch(name, pattern) for pattern in ("*.test.*", "*.spec.*")):
        return _explanation(SourceFileClassification.TEST_EVIDENCE, "glob", "test/spec filename pattern")
    return None


_SOURCE_TYPE_CLASSIFICATIONS: dict[SourceType, SourceFileClassification] = {
    SourceType.TESTS: SourceFileClassification.TEST_EVIDENCE,
    SourceType.DESIGN_DOCS: SourceFileClassification.DESIGN_DOC_EVIDENCE,
    SourceType.TICKETS: SourceFileClassification.TICKET_EVIDENCE,
    SourceType.FRONTEND_CODE: SourceFileClassification.UI_RULE_MIRROR,
    SourceType.BACKEND_CODE: SourceFileClassification.RULE_BEARING,
    SourceType.API_CONTRACT: SourceFileClassification.DOCUMENTATION_EVIDENCE,
}


def _match_source_type_signals(
    st: SourceType,
    suffix: str,
    parts: frozenset[str],
) -> ClassificationExplanation | None:
    if st == SourceType.BDD_SPECS or suffix == ".feature":
        return _explanation(SourceFileClassification.TEST_EVIDENCE, "source_type", st.value)
    if st == SourceType.DOCS or (suffix in {".md", ".rst"} and ("docs" in parts or "documentation" in parts)):
        signal = "source_type" if st == SourceType.DOCS else "path_rule"
        detail = st.value if st == SourceType.DOCS else "docs/**"
        return _explanation(SourceFileClassification.DOCUMENTATION_EVIDENCE, signal, detail)
    mapped = _SOURCE_TYPE_CLASSIFICATIONS.get(st)
    if mapped is not None:
        return _explanation(mapped, "source_type", st.value)
    return None


def explain_classification(
    path: Path | str,
    source_type: SourceType | str,
    *,
    override_pattern: str | None = None,
    override_classification: SourceFileClassification | str | None = None,
) -> ClassificationExplanation:
    """Return effective classification plus the signal that determined it."""
    if override_pattern and override_classification is not None:
        cls = (
            override_classification
            if isinstance(override_classification, SourceFileClassification)
            else SourceFileClassification(str(override_classification))
        )
        return _explanation(cls, "project_override", f"Project glob override: {override_pattern}")

    file_path = Path(path) if not isinstance(path, Path) else path
    _, name, parts = _normalized(file_path)
    suffix = file_path.suffix.lower()
    st = source_type if isinstance(source_type, SourceType) else SourceType(str(source_type))

    matched = _match_filename_signals(name, suffix, display_name=file_path.name)
    if matched is not None:
        return matched
    matched = _match_path_signals(parts, suffix)
    if matched is not None:
        return matched
    matched = _match_test_glob(name)
    if matched is not None:
        return matched
    matched = _match_source_type_signals(st, suffix, parts)
    if matched is not None:
        return matched

    if suffix in {".css", ".scss", ".png", ".jpg", ".svg", ".ico"}:
        return _explanation(SourceFileClassification.PRESENTATION_ONLY, "extension", suffix)

    return _explanation(
        SourceFileClassification.UNKNOWN_NEEDS_REVIEW,
        "fallback_unknown",
        "No filename, extension, path, or source-type rule matched",
    )
