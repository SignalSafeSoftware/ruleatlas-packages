"""Official Gherkin ingestion via gherkin-official."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import cast

from gherkin.errors import CompositeParserException, ParserException
from gherkin.parser import Parser
from gherkin.token_scanner import TokenScanner
from ruleatlas_persistence.models import BddFeature, BddScenario, BddStep
from ruleatlas_persistence.repositories import RepositoryFactory
from sqlalchemy.orm import Session

GHERKIN_PROVIDER_VERSION = "gherkin-official==41.0.0"


@dataclass
class GherkinParseResult:
    feature: BddFeature | None = None
    scenarios: list[BddScenario] = field(default_factory=list)
    steps: list[BddStep] = field(default_factory=list)
    error: str | None = None


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _tag_names(tags: list[dict] | None) -> list[str]:
    return [str(t.get("name") or "").lstrip("@") for t in (tags or []) if t.get("name")]


def _canonical_feature_key(source_path: str) -> str:
    return f"bdd:feature:{hashlib.sha256(source_path.encode()).hexdigest()[:16]}"


def _scenario_canonical_key(source_path: str, child_scenario: dict, name: str) -> str:
    digest = hashlib.sha256(f"{source_path}|{name}|{child_scenario.get('id')}".encode()).hexdigest()[:16]
    return f"bdd:scenario:{digest}"


def parse_gherkin_document(text: str) -> dict:
    parser = Parser()
    return cast(dict, parser.parse(TokenScanner(text)))


def _load_cached_feature_if_unchanged(
    repositories: RepositoryFactory,
    *,
    analysis_version_id: str,
    key: str,
    text: str,
) -> GherkinParseResult | None:
    existing = repositories.bdd_features().get_by_analysis_and_canonical_key(analysis_version_id, key)
    if existing is None or existing.content_hash != _content_hash(text):
        return None
    scenarios = repositories.bdd_scenarios().list_for_feature(existing.id)
    steps: list[BddStep] = []
    for scenario in scenarios:
        steps.extend(repositories.bdd_steps().list_for_scenario_ordered(scenario.id))
    return GherkinParseResult(feature=existing, scenarios=scenarios, steps=steps)


def _persist_parse_error_feature(
    session: Session,
    *,
    project_id: str,
    analysis_version_id: str,
    key: str,
    source_path: str,
    text: str,
    existing: BddFeature | None,
    error: str,
) -> GherkinParseResult:
    feature = existing or BddFeature(
        project_id=project_id,
        analysis_version_id=analysis_version_id,
        canonical_key=key,
        name=source_path,
        source_path=source_path,
        content_hash=_content_hash(text),
        tags_json=[],
        parse_error=error[:2000],
        attributes_json={"provider": GHERKIN_PROVIDER_VERSION},
    )
    if existing is not None:
        feature.parse_error = error[:2000]
        feature.content_hash = _content_hash(text)
    session.add(feature)
    session.commit()
    session.refresh(feature)
    return GherkinParseResult(feature=feature, error=error)


def _clear_feature_children(session: Session, repositories: RepositoryFactory, feature: BddFeature) -> None:
    old_scenarios = repositories.bdd_scenarios().list_for_feature(feature.id)
    for scenario in old_scenarios:
        old_steps = repositories.bdd_steps().list_for_scenario_ordered(scenario.id)
        for step in old_steps:
            session.delete(step)
        session.delete(scenario)
    session.flush()


def _new_feature_from_node(
    *,
    project_id: str,
    analysis_version_id: str,
    key: str,
    source_path: str,
    text: str,
    feature_node: dict,
) -> BddFeature:
    return BddFeature(
        project_id=project_id,
        analysis_version_id=analysis_version_id,
        canonical_key=key,
        name=str(feature_node.get("name") or source_path),
        language=str(feature_node.get("language") or "en"),
        source_path=source_path,
        start_line=(feature_node.get("location") or {}).get("line"),
        content_hash=_content_hash(text),
        tags_json=_tag_names(feature_node.get("tags")),
        description=feature_node.get("description") or None,
        parse_error=None,
        attributes_json={"provider": GHERKIN_PROVIDER_VERSION, "keyword": feature_node.get("keyword")},
    )


def _update_feature_from_node(feature: BddFeature, *, source_path: str, text: str, feature_node: dict) -> None:
    feature.name = str(feature_node.get("name") or source_path)
    feature.language = str(feature_node.get("language") or "en")
    feature.content_hash = _content_hash(text)
    feature.parse_error = None
    feature.tags_json = _tag_names(feature_node.get("tags"))


def _upsert_feature_from_node(
    session: Session,
    repositories: RepositoryFactory,
    *,
    project_id: str,
    analysis_version_id: str,
    key: str,
    source_path: str,
    text: str,
    feature_node: dict,
    existing: BddFeature | None,
) -> BddFeature:
    if existing is None:
        feature = _new_feature_from_node(
            project_id=project_id,
            analysis_version_id=analysis_version_id,
            key=key,
            source_path=source_path,
            text=text,
            feature_node=feature_node,
        )
        session.add(feature)
        session.flush()
        return feature

    feature = existing
    _update_feature_from_node(feature, source_path=source_path, text=text, feature_node=feature_node)
    session.add(feature)
    session.flush()
    _clear_feature_children(session, repositories, feature)
    return feature


def _build_scenario_examples(child_scenario: dict) -> list[dict]:
    examples: list[dict] = []
    for example in child_scenario.get("examples") or []:
        examples.append(
            {
                "name": example.get("name"),
                "tags": _tag_names(example.get("tags")),
                "table_header": (example.get("tableHeader") or {}).get("cells"),
                "table_body": [
                    [cell.get("value") for cell in (row.get("cells") or [])]
                    for row in (example.get("tableBody") or [])
                ],
            }
        )
    return examples


def _build_scenario(
    *,
    project_id: str,
    analysis_version_id: str,
    feature: BddFeature,
    source_path: str,
    child_scenario: dict,
    background: bool = False,
) -> BddScenario:
    name = str(child_scenario.get("name") or ("Background" if background else "Scenario"))
    is_outline = bool(child_scenario.get("examples"))
    return BddScenario(
        project_id=project_id,
        analysis_version_id=analysis_version_id,
        bdd_feature_id=feature.id,
        canonical_key=_scenario_canonical_key(source_path, child_scenario, name),
        name=name,
        keyword=str(child_scenario.get("keyword") or ("Background" if background else "Scenario")),
        is_outline=is_outline,
        start_line=(child_scenario.get("location") or {}).get("line"),
        tags_json=_tag_names(child_scenario.get("tags")),
        examples_json=_build_scenario_examples(child_scenario),
        attributes_json={
            "gherkin_id": child_scenario.get("id"),
            "background": background,
            "description": child_scenario.get("description"),
        },
    )


def _build_step(
    *,
    project_id: str,
    analysis_version_id: str,
    scenario: BddScenario,
    order: int,
    step: dict,
) -> BddStep:
    argument = None
    if step.get("dataTable"):
        argument = {"dataTable": step.get("dataTable")}
    if step.get("docString"):
        argument = {"docString": step.get("docString")}
    return BddStep(
        project_id=project_id,
        analysis_version_id=analysis_version_id,
        bdd_scenario_id=scenario.id,
        step_order=order,
        keyword=str(step.get("keyword") or "").strip(),
        keyword_type=step.get("keywordType"),
        text=str(step.get("text") or ""),
        start_line=(step.get("location") or {}).get("line"),
        argument_json=argument,
        attributes_json={"gherkin_id": step.get("id")},
    )


def _ingest_scenario(
    session: Session,
    *,
    project_id: str,
    analysis_version_id: str,
    feature: BddFeature,
    source_path: str,
    child_scenario: dict,
    background: bool = False,
) -> tuple[BddScenario, list[BddStep]]:
    scenario = _build_scenario(
        project_id=project_id,
        analysis_version_id=analysis_version_id,
        feature=feature,
        source_path=source_path,
        child_scenario=child_scenario,
        background=background,
    )
    session.add(scenario)
    session.flush()
    steps: list[BddStep] = []
    for order, step_node in enumerate(child_scenario.get("steps") or []):
        step = _build_step(
            project_id=project_id,
            analysis_version_id=analysis_version_id,
            scenario=scenario,
            order=order,
            step=step_node,
        )
        session.add(step)
        session.flush()
        steps.append(step)
    return scenario, steps


def _ingest_child_nodes(
    session: Session,
    *,
    project_id: str,
    analysis_version_id: str,
    feature: BddFeature,
    source_path: str,
    children: list[dict],
    scenarios_out: list[BddScenario],
    steps_out: list[BddStep],
) -> None:
    for child in children:
        if "background" in child:
            scenario, steps = _ingest_scenario(
                session,
                project_id=project_id,
                analysis_version_id=analysis_version_id,
                feature=feature,
                source_path=source_path,
                child_scenario=child["background"],
                background=True,
            )
            scenarios_out.append(scenario)
            steps_out.extend(steps)
        if "scenario" in child:
            scenario, steps = _ingest_scenario(
                session,
                project_id=project_id,
                analysis_version_id=analysis_version_id,
                feature=feature,
                source_path=source_path,
                child_scenario=child["scenario"],
                background=False,
            )
            scenarios_out.append(scenario)
            steps_out.extend(steps)


def _walk_feature_children(
    session: Session,
    *,
    project_id: str,
    analysis_version_id: str,
    feature: BddFeature,
    source_path: str,
    feature_node: dict,
) -> tuple[list[BddScenario], list[BddStep]]:
    scenarios_out: list[BddScenario] = []
    steps_out: list[BddStep] = []
    children = feature_node.get("children") or []
    _ingest_child_nodes(
        session,
        project_id=project_id,
        analysis_version_id=analysis_version_id,
        feature=feature,
        source_path=source_path,
        children=children,
        scenarios_out=scenarios_out,
        steps_out=steps_out,
    )
    for child in children:
        rule = child.get("rule")
        if not rule:
            continue
        _ingest_child_nodes(
            session,
            project_id=project_id,
            analysis_version_id=analysis_version_id,
            feature=feature,
            source_path=source_path,
            children=rule.get("children") or [],
            scenarios_out=scenarios_out,
            steps_out=steps_out,
        )
    return scenarios_out, steps_out


def ingest_feature_file(
    session: Session,
    *,
    project_id: str,
    analysis_version_id: str,
    source_path: str,
    text: str,
) -> GherkinParseResult:
    key = _canonical_feature_key(source_path)
    repositories = RepositoryFactory(session)
    existing = repositories.bdd_features().get_by_analysis_and_canonical_key(analysis_version_id, key)

    cached = _load_cached_feature_if_unchanged(
        repositories,
        analysis_version_id=analysis_version_id,
        key=key,
        text=text,
    )
    if cached is not None:
        return cached

    try:
        doc = parse_gherkin_document(text)
    except (CompositeParserException, ParserException, ValueError, TypeError, AttributeError) as exc:
        return _persist_parse_error_feature(
            session,
            project_id=project_id,
            analysis_version_id=analysis_version_id,
            key=key,
            source_path=source_path,
            text=text,
            existing=existing,
            error=str(exc),
        )

    feature_node = doc.get("feature") or {}
    if not feature_node:
        return _persist_parse_error_feature(
            session,
            project_id=project_id,
            analysis_version_id=analysis_version_id,
            key=key,
            source_path=source_path,
            text=text,
            existing=None,
            error="No Feature found in document",
        )

    feature = _upsert_feature_from_node(
        session,
        repositories,
        project_id=project_id,
        analysis_version_id=analysis_version_id,
        key=key,
        source_path=source_path,
        text=text,
        feature_node=feature_node,
        existing=existing,
    )
    scenarios_out, steps_out = _walk_feature_children(
        session,
        project_id=project_id,
        analysis_version_id=analysis_version_id,
        feature=feature,
        source_path=source_path,
        feature_node=feature_node,
    )

    session.commit()
    session.refresh(feature)
    return GherkinParseResult(feature=feature, scenarios=scenarios_out, steps=steps_out)
