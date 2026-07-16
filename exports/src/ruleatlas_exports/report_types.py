from enum import StrEnum

__all__ = [
    "ANALYSIS_VERSION_SCOPED_EXPORT_SLUGS",
    "EXPORT_REPORT_METADATA",
    "ExportReportSlug",
]


class ExportReportSlug(StrEnum):
    BUSINESS_RULES = "business-rules"
    EVIDENCE_MATRIX = "evidence-matrix"
    CONFLICTS = "conflicts"
    IMPLEMENTATION_GAPS = "implementation-gaps"
    SCAN_SUMMARY = "scan-summary"
    COVERAGE_EVIDENCE = "coverage-evidence"
    RUNTIME_EVIDENCE = "runtime-evidence"
    DISCOVERY_REPORT = "discovery-report"
    DISCOVERY_INVENTORY_CSV = "discovery-inventory-csv"
    DISCOVERY_INVENTORY_JSON = "discovery-inventory-json"
    BUSINESS_RULES_CSV = "business-rules-csv"
    BUSINESS_RULES_JSON = "business-rules-json"
    CONFLICTS_CSV = "conflicts-csv"
    CONFLICTS_JSON = "conflicts-json"
    IMPLEMENTATION_GAPS_CSV = "implementation-gaps-csv"
    IMPLEMENTATION_GAPS_JSON = "implementation-gaps-json"
    ANALYSIS_COMPARE_CSV = "analysis-compare-csv"
    ANALYSIS_COMPARE_JSON = "analysis-compare-json"
    ANALYSIS_COMPARE_MD = "analysis-compare-md"


ANALYSIS_VERSION_SCOPED_EXPORT_SLUGS = frozenset(
    {
        ExportReportSlug.BUSINESS_RULES,
        ExportReportSlug.EVIDENCE_MATRIX,
        ExportReportSlug.CONFLICTS,
        ExportReportSlug.IMPLEMENTATION_GAPS,
        ExportReportSlug.COVERAGE_EVIDENCE,
        ExportReportSlug.RUNTIME_EVIDENCE,
        ExportReportSlug.BUSINESS_RULES_CSV,
        ExportReportSlug.BUSINESS_RULES_JSON,
        ExportReportSlug.CONFLICTS_CSV,
        ExportReportSlug.CONFLICTS_JSON,
        ExportReportSlug.IMPLEMENTATION_GAPS_CSV,
        ExportReportSlug.IMPLEMENTATION_GAPS_JSON,
    }
)


EXPORT_REPORT_METADATA: dict[ExportReportSlug, dict[str, str]] = {
    ExportReportSlug.BUSINESS_RULES: {
        "filename": "business-rules.md",
        "title": "Business Rules",
        "description": "Candidate and reviewed rules with status and confidence.",
    },
    ExportReportSlug.EVIDENCE_MATRIX: {
        "filename": "evidence-matrix.md",
        "title": "Evidence Matrix",
        "description": "Rule evidence rows with source types, paths, and line ranges.",
    },
    ExportReportSlug.CONFLICTS: {
        "filename": "conflicts.md",
        "title": "Conflicts",
        "description": "Detected mismatches between sources.",
    },
    ExportReportSlug.IMPLEMENTATION_GAPS: {
        "filename": "implementation-gaps.md",
        "title": "Implementation Gaps",
        "description": "Open gaps between expected and observed behavior.",
    },
    ExportReportSlug.SCAN_SUMMARY: {
        "filename": "scan-summary.md",
        "title": "Scan Summary",
        "description": "Scan run stages, counts, and pipeline summary.",
    },
    ExportReportSlug.COVERAGE_EVIDENCE: {
        "filename": "coverage-evidence.md",
        "title": "Coverage Evidence",
        "description": "Coverage assessments linked to rules (supporting evidence only).",
    },
    ExportReportSlug.RUNTIME_EVIDENCE: {
        "filename": "runtime-evidence.md",
        "title": "Runtime Evidence",
        "description": "Imported runtime log findings (supporting evidence only).",
    },
    ExportReportSlug.DISCOVERY_REPORT: {
        "filename": "discovery-report.md",
        "title": "Discovery Report",
        "description": "Inventory, classifications, scope, and source health for a scan run.",
        "content_format": "markdown",
    },
    ExportReportSlug.DISCOVERY_INVENTORY_CSV: {
        "filename": "discovery-inventory.csv",
        "title": "Discovery Inventory (CSV)",
        "description": "Full discovered file inventory with detected/effective classification (machine-readable).",
        "content_format": "csv",
    },
    ExportReportSlug.DISCOVERY_INVENTORY_JSON: {
        "filename": "discovery-inventory.json",
        "title": "Discovery Inventory (JSON)",
        "description": "Full discovered file inventory with metadata (machine-readable).",
        "content_format": "json",
    },
    ExportReportSlug.BUSINESS_RULES_CSV: {
        "filename": "business-rules.csv",
        "title": "Business Rules (CSV)",
        "description": "Rules for the active or selected analysis version (machine-readable).",
        "content_format": "csv",
    },
    ExportReportSlug.BUSINESS_RULES_JSON: {
        "filename": "business-rules.json",
        "title": "Business Rules (JSON)",
        "description": "Rules for the active or selected analysis version with export metadata.",
        "content_format": "json",
    },
    ExportReportSlug.CONFLICTS_CSV: {
        "filename": "conflicts.csv",
        "title": "Conflicts (CSV)",
        "description": "Review conflicts for the active or selected analysis version (machine-readable).",
        "content_format": "csv",
    },
    ExportReportSlug.CONFLICTS_JSON: {
        "filename": "conflicts.json",
        "title": "Conflicts (JSON)",
        "description": "Review conflicts for the active or selected analysis version with export metadata.",
        "content_format": "json",
    },
    ExportReportSlug.IMPLEMENTATION_GAPS_CSV: {
        "filename": "implementation-gaps.csv",
        "title": "Implementation Gaps (CSV)",
        "description": "Review gaps for the active or selected analysis version (machine-readable).",
        "content_format": "csv",
    },
    ExportReportSlug.IMPLEMENTATION_GAPS_JSON: {
        "filename": "implementation-gaps.json",
        "title": "Implementation Gaps (JSON)",
        "description": "Review gaps for the active or selected analysis version with export metadata.",
        "content_format": "json",
    },
    ExportReportSlug.ANALYSIS_COMPARE_CSV: {
        "filename": "analysis-compare.csv",
        "title": "Analysis Compare (CSV)",
        "description": "Read-only diff between two analysis versions (machine-readable).",
        "content_format": "csv",
    },
    ExportReportSlug.ANALYSIS_COMPARE_JSON: {
        "filename": "analysis-compare.json",
        "title": "Analysis Compare (JSON)",
        "description": "Read-only diff between two analysis versions with export metadata.",
        "content_format": "json",
    },
    ExportReportSlug.ANALYSIS_COMPARE_MD: {
        "filename": "analysis-compare.md",
        "title": "Analysis Compare (Markdown)",
        "description": "Narrative read-only diff between two analysis versions with trust notices.",
        "content_format": "markdown",
    },
}
