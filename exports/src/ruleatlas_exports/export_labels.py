from __future__ import annotations

from ruleatlas_contracts.enums import EvidenceSourceType

__all__ = [
    "PRODUCT_INTENT_EVIDENCE",
    "SOURCE_ROLE_STRENGTH",
    "STATUS_LABELS",
    "human_status_label",
    "source_role_strength",
    "source_type_label",
    "trust_notice_for",
]

PRODUCT_INTENT_EVIDENCE = "Product-intent evidence"

STATUS_LABELS = {
    "candidate": "Candidate",
    "needs_review": "Needs review",
    "approved": "Approved",
    "rejected": "Rejected",
    "needs_follow_up": "Needs follow-up",
    "deprecated": "Deprecated",
    "open": "Open",
    "investigating": "Investigating",
    "resolved": "Resolved",
    "dismissed": "Dismissed",
    "accepted": "Accepted",
    "planned": "Planned",
    "in_progress": "In progress",
}

SOURCE_ROLE_STRENGTH = {
    EvidenceSourceType.BACKEND_CODE.value: "Strong implementation evidence",
    EvidenceSourceType.FRONTEND_CODE.value: "UI / mirror evidence",
    EvidenceSourceType.UNIT_TEST.value: "Expected-behavior evidence (domain tests)",
    EvidenceSourceType.INTEGRATION_TEST.value: "Expected-behavior evidence (domain tests)",
    EvidenceSourceType.BDD_SPEC.value: "Product-intent / expected-behavior evidence",
    EvidenceSourceType.README_DOC.value: PRODUCT_INTENT_EVIDENCE,
    EvidenceSourceType.DESIGN_DOC.value: PRODUCT_INTENT_EVIDENCE,
    EvidenceSourceType.TICKET.value: PRODUCT_INTENT_EVIDENCE,
    EvidenceSourceType.API_CONTRACT.value: "Contract evidence",
    EvidenceSourceType.CODE_COMMENT.value: "Weak evidence (comments)",
    EvidenceSourceType.AI_EXTRACTION.value: "Candidate-only (AI)",
    EvidenceSourceType.COVERAGE_REPORT.value: "Test-execution evidence only",
    EvidenceSourceType.RUNTIME_LOG.value: "Observed behavior only",
}


def human_status_label(status: str) -> str:
    return STATUS_LABELS.get(status, status.replace("_", " ").title())


def source_type_label(source_type: str) -> str:
    return source_type.replace("_", " ")


def source_role_strength(source_type: str) -> str:
    return SOURCE_ROLE_STRENGTH.get(source_type, "Supporting evidence")


def trust_notice_for(report_kind: str) -> str:
    notices = {
        "business_rules": (
            "> **Review notice:** Rules with status Candidate or Needs review are not confirmed "
            "product intent. AI extraction, coverage, runtime logs, and code comments are supporting "
            "signals only — they never auto-approve a rule. Human review is required before treating "
            "any row as an approved business rule.\n"
        ),
        "evidence": (
            "> **Review notice:** Evidence supports or challenges claims. It does not auto-approve "
            "product intent. AI, coverage, runtime, and comments never confirm a rule alone.\n"
        ),
        "conflicts": (
            "> **Review notice:** Conflicts are review findings, not confirmed defects or final "
            "product truth. Human review is required before treating a conflict as a product or "
            "implementation issue.\n"
        ),
        "gaps": (
            "> **Review notice:** Gaps are review findings, not confirmed missing work or product "
            "defects. Coverage-framed gaps are test-execution evidence only and do not confirm "
            "product intent. Human review is required.\n"
        ),
        "coverage": (
            "> **Review notice:** Coverage is test-execution evidence only. It supports or challenges "
            "claims but does not confirm product intent.\n"
        ),
        "runtime": (
            "> **Review notice:** Runtime logs are observed-behavior evidence only. Denials and "
            "events do not confirm product intent alone.\n"
        ),
        "discovery": (
            "> **Discovery notice:** This report describes **inventory and scan scope only**. It does "
            "**not** approve rules or confirm product intent. Files listed here are not business rules. "
            "Coverage artifacts are **test-execution evidence** (detection only until full scan import). "
            "Runtime artifacts are **observed behavior** (detection only). Include/exclude filters affect "
            "what is scanned; they do **not** delete source locations. AI extraction produces "
            "candidate-only claims. **Human review is required** before treating any rule as approved "
            "business intent.\n"
        ),
        "compare": (
            "> **Compare notice:** This export is a read-only diff between two analysis versions. "
            "It does not activate a version, approve rules, or confirm conflicts/gaps as product truth. "
            "Human review is required.\n"
        ),
    }
    return notices.get(report_kind, notices["business_rules"])
