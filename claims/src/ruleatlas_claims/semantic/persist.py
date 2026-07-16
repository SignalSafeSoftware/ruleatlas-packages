"""Persist semantic provider results as SemanticObservation rows."""

from __future__ import annotations

import logging

from ruleatlas_contracts.enums import SemanticProviderStatus
from ruleatlas_contracts.semantic_contract import SemanticAnalysisResult, SemanticProvider
from ruleatlas_persistence.models import SemanticObservation
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def persist_semantic_result(
    session: Session,
    *,
    project_id: str,
    analysis_version_id: str,
    result: SemanticAnalysisResult,
) -> int:
    count = 0
    for sym in result.symbols:
        session.add(
            SemanticObservation(
                project_id=project_id,
                analysis_version_id=analysis_version_id,
                provider_key=result.provider_key,
                provider_version=result.provider_version,
                observation_kind="symbol",
                symbol_key=sym.symbol_key,
                source_path=sym.source_path,
                start_line=sym.start_line,
                end_line=sym.end_line,
                confidence=sym.confidence,
                status=result.status,
                payload_json={"display_name": sym.display_name, "kind": sym.kind, **sym.attributes},
                attributes_json={},
            )
        )
        count += 1
    for ref in result.references:
        session.add(
            SemanticObservation(
                project_id=project_id,
                analysis_version_id=analysis_version_id,
                provider_key=result.provider_key,
                provider_version=result.provider_version,
                observation_kind="reference",
                symbol_key=ref.from_symbol_key,
                source_path=ref.source_path,
                start_line=ref.start_line,
                confidence=ref.confidence,
                status=result.status,
                resolution_type=ref.resolution_type,
                payload_json={
                    "to_symbol_key": ref.to_symbol_key,
                    "reference_kind": ref.reference_kind,
                    **ref.attributes,
                },
                attributes_json={},
            )
        )
        count += 1
    if result.status in {
        SemanticProviderStatus.FAILED.value,
        SemanticProviderStatus.DEGRADED.value,
        SemanticProviderStatus.UNAVAILABLE.value,
    }:
        session.add(
            SemanticObservation(
                project_id=project_id,
                analysis_version_id=analysis_version_id,
                provider_key=result.provider_key,
                provider_version=result.provider_version,
                observation_kind="provider_status",
                confidence=0.0,
                status=result.status,
                payload_json={"error": result.error_message, "summary": result.summary},
                attributes_json={"baseline_continues": True},
            )
        )
        count += 1
    session.commit()
    return count


def run_optional_semantic_provider(
    session: Session,
    provider: SemanticProvider,
    *,
    project_id: str,
    analysis_version_id: str,
    root: str,
    relative_paths: list[str] | None = None,
) -> SemanticAnalysisResult:
    """Run provider; failures never raise to callers — returns degraded result."""
    try:
        result = provider.analyze_paths(root, relative_paths or [])
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        logger.exception(
            "Optional semantic provider failed provider=%s project_id=%s",
            provider.__class__.__name__,
            project_id,
        )
        result = SemanticAnalysisResult(
            provider_key=getattr(provider.capabilities(), "provider_key", "unknown"),
            provider_version=getattr(provider.capabilities(), "provider_version", "1"),
            status=SemanticProviderStatus.FAILED.value,
            error_message=str(exc),
            summary={"baseline_continues": True},
        )
    persist_semantic_result(
        session,
        project_id=project_id,
        analysis_version_id=analysis_version_id,
        result=result,
    )
    return result
