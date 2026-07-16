"""Remote AI usage metering and cost estimation."""

from __future__ import annotations

from datetime import UTC, datetime

from ruleatlas_contracts.enums import AiProviderMode
from ruleatlas_persistence.models import AiModelUsage
from ruleatlas_persistence.repositories import RepositoryFactory
from sqlalchemy.orm import Session

# Rough USD per 1M tokens (planning estimates — not billing-grade).
_MODEL_INPUT_COST_PER_M: dict[str, float] = {
    "gpt-4o-mini": 0.15,
    "gpt-4o": 2.50,
    "gpt-4.1-mini": 0.40,
    "gpt-5.5": 1.25,
    "gpt-5.5-pro": 5.00,
    "gpt-5-mini": 0.25,
}
_MODEL_OUTPUT_COST_PER_M: dict[str, float] = {
    "gpt-4o-mini": 0.60,
    "gpt-4o": 10.00,
    "gpt-4.1-mini": 1.60,
    "gpt-5.5": 10.00,
    "gpt-5.5-pro": 25.00,
    "gpt-5-mini": 2.00,
}
_DEFAULT_INPUT_COST = 0.50
_DEFAULT_OUTPUT_COST = 1.50


def estimate_cost_usd(model: str, *, prompt_tokens: int, completion_tokens: int) -> float:
    input_rate = _MODEL_INPUT_COST_PER_M.get(model, _DEFAULT_INPUT_COST)
    output_rate = _MODEL_OUTPUT_COST_PER_M.get(model, _DEFAULT_OUTPUT_COST)
    return (prompt_tokens * input_rate + completion_tokens * output_rate) / 1_000_000


def record_ai_usage(
    session: Session,
    *,
    project_id: str | None,
    scan_run_id: str | None,
    model_name: str,
    prompt_tokens: int,
    completion_tokens: int,
    provider_mode: AiProviderMode = AiProviderMode.OPENAI_REMOTE,
) -> AiModelUsage:
    cost = estimate_cost_usd(model_name, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
    row = AiModelUsage(
        project_id=project_id,
        scan_run_id=scan_run_id,
        provider_mode=provider_mode,
        model_name=model_name,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_cost_usd=cost,
    )
    session.add(row)
    session.flush()
    return row


def org_remote_spend_usd(session: Session, organization_id: str) -> float:
    """Sum remote AI spend for org projects in the current UTC calendar month."""
    repos = RepositoryFactory(session)
    now = datetime.now(UTC)
    month_start = datetime(now.year, now.month, 1, tzinfo=UTC)
    project_ids = repos.projects().list_ids_for_organization(organization_id)
    return repos.ai_model_usage().sum_remote_spend_for_projects(project_ids, since=month_start)


def list_org_ai_usage_summary(session: Session, organization_id: str, *, limit: int = 50) -> list[dict[str, object]]:
    repos = RepositoryFactory(session)
    project_ids = repos.projects().list_ids_for_organization(organization_id)
    rows = repos.ai_model_usage().list_for_projects(project_ids, limit=limit)
    return [
        {
            "id": row.id,
            "project_id": row.project_id,
            "model_name": row.model_name,
            "provider_mode": row.provider_mode.value if hasattr(row.provider_mode, "value") else str(row.provider_mode),
            "prompt_tokens": row.prompt_tokens,
            "completion_tokens": row.completion_tokens,
            "total_cost_usd": row.total_cost_usd,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]
