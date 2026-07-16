"""Link Gherkin steps to step-definition patterns across languages."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TypedDict

from ruleatlas_contracts.enums import BddStepLinkStatus
from ruleatlas_persistence.models import BddStepLink
from ruleatlas_persistence.repositories import RepositoryFactory
from sqlalchemy.orm import Session

# Common step-definition decorators / attributes
_DEF_PATTERNS = (
    # Python: pytest-bdd @given(parsers.parse('...'))
    re.compile(
        r"""@(?:given|when|then|step)\s*\(\s*parsers\.(?:parse|re)\s*\(\s*['"](.+?)['"]\s*\)\s*\)\s*\n\s*(?:async\s+)?def\s+(\w+)""",
        re.I | re.M,
    ),
    # Python: behave / pytest-bdd
    re.compile(
        r"""@(?:given|when|then|step)\s*\(\s*['"](.+?)['"]\s*\)\s*\n\s*(?:async\s+)?def\s+(\w+)""",
        re.I | re.M,
    ),
    re.compile(
        r"""@parsers\.(?:parse|re)\s*\(\s*['"](.+?)['"]\s*\)\s*\n\s*def\s+(\w+)""",
        re.I | re.M,
    ),
    # TypeScript: cucumber
    re.compile(
        r"""(?:Given|When|Then|And|But)\s*\(\s*['"`](.+?)['"`]\s*,\s*(?:async\s*)?(?:function|\()""",
        re.M,
    ),
    # C#: Req / SpecFlow / Reqnroll
    re.compile(
        r"""\[(?:Given|When|Then|And|But)\s*\(\s*"(.+?)"\s*\)\]\s*\n\s*(?:public\s+)?(?:async\s+)?(?:void|Task)\s+(\w+)""",
        re.I | re.M,
    ),
    # PHP: Behat
    re.compile(
        r"""#\[(?:Given|When|Then|And|But)\s*\(\s*['"](.+?)['"]\s*\)\]\s*\n\s*public\s+function\s+(\w+)""",
        re.I | re.M,
    ),
    re.compile(
        r"""\*\s*@(?:Given|When|Then|And|But)\s+(.+?)\s*\*/\s*\n\s*public\s+function\s+(\w+)""",
        re.I | re.M,
    ),
)


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


def discover_step_definitions(files: dict[str, str]) -> list[StepDefinition]:
    found: list[StepDefinition] = []
    for path, text in files.items():
        for pattern in _DEF_PATTERNS:
            for match in pattern.finditer(text):
                expr = match.group(1)
                name = match.group(2) if match.lastindex and match.lastindex >= 2 else expr[:40]
                line = text[: match.start()].count("\n") + 1
                try:
                    rx = compile_pattern(expr)
                except re.error:
                    continue
                found.append(
                    StepDefinition(pattern=expr, name=name, path=path, start_line=line, regex=rx)
                )
    return found


def link_steps(
    session: Session,
    *,
    project_id: str,
    analysis_version_id: str,
    definitions: list[StepDefinition],
) -> dict:
    repositories = RepositoryFactory(session)
    steps = repositories.bdd_steps().list_all_for_analysis(project_id, analysis_version_id)
    linked = ambiguous = undefined = 0
    for step in steps:
        # Clear prior links for re-link
        old_links = repositories.bdd_step_links().list_for_step(step.id)
        for old_link in old_links:
            session.delete(old_link)
        candidates: list[StepLinkCandidate] = []
        for definition in definitions:
            if definition.regex.match(step.text.strip()):
                candidates.append(
                    {
                        "pattern": definition.pattern,
                        "name": definition.name,
                        "path": definition.path,
                        "start_line": definition.start_line,
                    }
                )
        if not candidates:
            status = BddStepLinkStatus.UNDEFINED.value
            undefined += 1
            confidence = 0.0
            primary: StepLinkCandidate | None = None
        elif len(candidates) == 1:
            status = BddStepLinkStatus.LINKED.value
            linked += 1
            confidence = 0.85
            primary = candidates[0]
        else:
            status = BddStepLinkStatus.AMBIGUOUS.value
            ambiguous += 1
            confidence = 0.4
            primary = candidates[0]
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
        "linked": linked,
        "ambiguous": ambiguous,
        "undefined": undefined,
    }
