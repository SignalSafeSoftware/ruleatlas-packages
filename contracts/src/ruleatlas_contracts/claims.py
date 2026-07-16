"""Candidate-claim transport DTO (breakup Phase 2).

``ClaimDraft`` is the provider-neutral shape emitted by the extraction, AI, and structural (Semgrep/semantic)
providers and consumed by the persistence layer. It lives in the kernel so the extraction, claims, and ai
packages can share it without importing one another (this is what lets us break the extraction<->claims and
ai<->claims cycles).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ruleatlas_contracts.enums import SourceClaimRole

__all__ = ["ClaimDraft"]


@dataclass
class ClaimDraft:
    claim_text: str
    provider_key: str
    claim_role: str = SourceClaimRole.IMPLEMENTATION.value
    confidence: float = 0.3
    actor: str | None = None
    condition_text: str | None = None
    action_text: str | None = None
    result_text: str | None = None
    exception_text: str | None = None
    subject_text: str | None = None
    state_transition: str | None = None
    source_path: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    provider_version: str | None = None
    graph_node_id: str | None = None
    evidence: list[dict[str, Any]] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)
