"""Link Gherkin steps to step-definition patterns across languages."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TypedDict

from ruleatlas_contracts.enums import BddStepLinkStatus
from ruleatlas_persistence.models import BddStepLink
from ruleatlas_persistence.repositories import RepositoryFactory
from sqlalchemy.orm import Session

# Single-line decorator matches — no spanning `\s*` / `\n` (Sonar S8786 / S5843).
_PY_PARSER_DECORATOR = re.compile(
    r"^@(?:given|when|then|step)\(parsers\.(?:parse|re)\(['\"]([^'\"]{1,400})['\"]",
    re.I,
)
_PY_SIMPLE_DECORATOR = re.compile(
    r"^@(?:given|when|then|step)\(['\"]([^'\"]{1,400})['\"]",
    re.I,
)
_PY_PARSERS_ATTR = re.compile(
    r"^@parsers\.(?:parse|re)\(['\"]([^'\"]{1,400})['\"]",
    re.I,
)
_PY_FUNC = re.compile(r"(?:async[ \t]+)?def[ \t]+(\w+)", re.I)
_TS_STEP = re.compile(r"^(?:Given|When|Then|And|But)\(['\"`]([^'\"`]{1,400})['\"`]")
_CS_ATTR = re.compile(r"^\[(?:Given|When|Then|And|But)\(\"([^\"]{1,400})\"\)\]", re.I)
_CS_FUNC = re.compile(r"(?:public[ \t]+)?(?:async[ \t]+)?(?:void|Task)[ \t]+(\w+)", re.I)
_PHP_ATTR = re.compile(
    r"^#\[(?:Given|When|Then|And|But)\(['\"]([^'\"]{1,400})['\"]\)\]",
    re.I,
)
_PHP_DOCBLOCK = re.compile(r"\*[ \t]*@(?:Given|When|Then|And|But)[ \t]+([^\n*]{1,400})", re.I)
_PHP_FUNC = re.compile(r"public[ \t]+function[ \t]+(\w+)", re.I)


@dataclass
class StepDefinition:
    pattern: str
    name: str
    path: str
    start_line: int
    regex: re.Pattern[str]


class StepLinkCandidate(TypedDict):
    pattern: str
    name: str
    path: str
    start_line: int


def compile_pattern(pattern: str) -> re.Pattern[str]:
    """Convert cucumber-ish `{word}` / `{int}` and `(.*)` patterns to regex."""
    escaped = re.escape(pattern)
    escaped = escaped.replace(r"\{word\}", r"([^\"]+)").replace(r"\{int\}", r"(\d+)")
    escaped = escaped.replace(r"\{string\}", r"\"([^\"]*)\"|([^\"\\s]+)")
    # already-regex fragments like (.*) were escaped — restore common ones carefully
    return re.compile("^" + escaped.replace(r"\(\.\*\)", "(.*)") + "$", re.I)


def _lookahead_name(lines: list[str], index: int, pattern: re.Pattern[str]) -> str | None:
    for line in lines[index + 1 : index + 4]:
        match = pattern.search(line)
        if match:
            return match.group(1)
    return None


def _python_step_expr(line: str) -> str | None:
    match = (
        _PY_PARSER_DECORATOR.search(line)
        or _PY_SIMPLE_DECORATOR.search(line)
        or _PY_PARSERS_ATTR.search(line)
    )
    return match.group(1) if match else None


def _decorator_match(line: str) -> tuple[str, re.Pattern[str] | None] | None:
    expr = _python_step_expr(line)
    if expr is not None:
        return expr, _PY_FUNC
    match = _CS_ATTR.search(line)
    if match:
        return match.group(1), _CS_FUNC
    match = _PHP_ATTR.search(line) or _PHP_DOCBLOCK.search(line)
    if match:
        return match.group(1), _PHP_FUNC
    match = _TS_STEP.search(line)
    if match:
        return match.group(1), None
    return None


def discover_step_definitions(files: dict[str, str]) -> list[StepDefinition]:
    found: list[StepDefinition] = []
    for path, text in files.items():
        lines = text.splitlines()
        for index, line in enumerate(lines):
            matched = _decorator_match(line.strip())
            if matched is None:
                continue
            expr, name_pattern = matched
            name = _lookahead_name(lines, index, name_pattern) if name_pattern else None
            name = name or expr[:40]
            try:
                rx = compile_pattern(expr)
            except re.error:
                continue
            found.append(
                StepDefinition(pattern=expr, name=name, path=path, start_line=index + 1, regex=rx)
            )
    return found


def _candidates_for_step(step_text: str, definitions: list[StepDefinition]) -> list[StepLinkCandidate]:
    return [
        {
            "pattern": definition.pattern,
            "name": definition.name,
            "path": definition.path,
            "start_line": definition.start_line,
        }
        for definition in definitions
        if definition.regex.match(step_text.strip())
    ]


def _status_for_candidates(
    candidates: list[StepLinkCandidate],
) -> tuple[str, float, StepLinkCandidate | None, str]:
    if not candidates:
        return BddStepLinkStatus.UNDEFINED.value, 0.0, None, "undefined"
    if len(candidates) == 1:
        return BddStepLinkStatus.LINKED.value, 0.85, candidates[0], "linked"
    return BddStepLinkStatus.AMBIGUOUS.value, 0.4, candidates[0], "ambiguous"


def link_steps(
    session: Session,
    *,
    project_id: str,
    analysis_version_id: str,
    definitions: list[StepDefinition],
) -> dict:
    repositories = RepositoryFactory(session)
    steps = repositories.bdd_steps().list_all_for_analysis(project_id, analysis_version_id)
    counts = {"linked": 0, "ambiguous": 0, "undefined": 0}
    for step in steps:
        for old_link in repositories.bdd_step_links().list_for_step(step.id):
            session.delete(old_link)
        candidates = _candidates_for_step(step.text, definitions)
        status, confidence, primary, bucket = _status_for_candidates(candidates)
        counts[bucket] += 1
        graph_node_id = None
        if primary:
            node = repositories.graph_nodes().get_by_display_name(
                project_id, analysis_version_id, primary["name"]
            )
            if node is not None:
                graph_node_id = node.id
        session.add(
            BddStepLink(
                project_id=project_id,
                analysis_version_id=analysis_version_id,
                bdd_step_id=step.id,
                status=status,
                definition_path=primary["path"] if primary else None,
                definition_name=primary["name"] if primary else None,
                definition_start_line=primary["start_line"] if primary else None,
                graph_node_id=graph_node_id,
                confidence=confidence,
                candidates_json=candidates,
                attributes_json={},
            )
        )
        step.link_status = status
        session.add(step)
    session.commit()
    return {
        "steps_total": len(steps),
        "linked": counts["linked"],
        "ambiguous": counts["ambiguous"],
        "undefined": counts["undefined"],
    }
