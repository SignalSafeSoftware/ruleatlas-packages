"""Additional domain repositories for full sqlPhilosophy query-boundary coverage."""

from __future__ import annotations

from typing import TYPE_CHECKING, SupportsInt, cast

from ruleatlas_contracts.enums import (
    ImplementationGapStatus,
    RuleConflictStatus,
    RuleStatus,
    ScanStatus,
)
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from ruleatlas_persistence.models import (
    ImplementationGap,
    Rule,
    RuleConflict,
    RuleCoverageAssessment,
    RuntimeLogEvidence,
    ScanRun,
    SourceLocation,
)

if TYPE_CHECKING:
    from ruleatlas_persistence.repositories.factory import RepositoryFactory


class ProjectSummaryRepository:
    def __init__(self, session: Session, factory: RepositoryFactory) -> None:
        self._rules = factory.rules()
        self._conflicts = factory.conflicts()
        self._gaps = factory.gaps()
        self._scan_runs = factory.scan_runs()
        self._source_locations = factory.source_locations()
        self._coverage_assessments = factory.coverage_assessments()
        self._runtime_evidence = factory.runtime_log_evidence()

    def fetch_counts(self, project_id: str, active_version_id: str | None) -> dict[str, int]:
        rule_filters = [Rule.project_id == project_id]
        conflict_filters = [RuleConflict.project_id == project_id]
        gap_filters = [ImplementationGap.project_id == project_id]
        if active_version_id:
            rule_filters.append(Rule.analysis_version_id == active_version_id)
            conflict_filters.append(RuleConflict.analysis_version_id == active_version_id)
            gap_filters.append(ImplementationGap.analysis_version_id == active_version_id)

        rule_counts = (
            self._rules.statement()
            .select_columns(
                func.count().label("total"),
                func.coalesce(
                    func.sum(case((Rule.status == RuleStatus.APPROVED, 1), else_=0)),
                    0,
                ).label("approved"),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                Rule.status.in_([RuleStatus.CANDIDATE, RuleStatus.NEEDS_REVIEW]),
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label("candidate"),
            )
            .where(*rule_filters)
            .mappings()
            .one()
        )

        conflict_counts = (
            self._conflicts.statement()
            .select_columns(
                func.count().label("total"),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                RuleConflict.status.in_(
                                    [
                                        RuleConflictStatus.OPEN,
                                        RuleConflictStatus.INVESTIGATING,
                                    ]
                                ),
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label("open"),
            )
            .where(*conflict_filters)
            .mappings()
            .one()
        )

        gap_counts = (
            self._gaps.statement()
            .select_columns(
                func.count().label("total"),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                (ImplementationGap.title.ilike("%coverage gap%"))
                                & (ImplementationGap.status == ImplementationGapStatus.OPEN),
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label("coverage"),
            )
            .where(*gap_filters)
            .mappings()
            .one()
        )

        scan_counts = (
            self._scan_runs.statement()
            .select_columns(
                func.count().label("total"),
                func.coalesce(
                    func.sum(case((ScanRun.status == ScanStatus.FAILED, 1), else_=0)),
                    0,
                ).label("failed"),
            )
            .where(ScanRun.project_id == project_id)
            .mappings()
            .one()
        )

        source_location_count = (
            self._source_locations.statement().where(SourceLocation.project_id == project_id).count()
        )
        coverage_assessment_count = (
            self._coverage_assessments.statement()
            .join(Rule, RuleCoverageAssessment.rule_id == Rule.id)
            .where(Rule.project_id == project_id)
            .count()
        )
        runtime_finding_count = (
            self._runtime_evidence.statement().where(RuntimeLogEvidence.project_id == project_id).count()
        )

        def count_value(value: object) -> int:
            return int(cast(str | bytes | SupportsInt, value or 0))

        return {
            "rule_count": count_value(rule_counts["total"]),
            "approved_rule_count": count_value(rule_counts["approved"]),
            "candidate_rule_count": count_value(rule_counts["candidate"]),
            "conflict_count": count_value(conflict_counts["total"]),
            "open_conflict_count": count_value(conflict_counts["open"]),
            "gap_count": count_value(gap_counts["total"]),
            "coverage_gap_count": count_value(gap_counts["coverage"]),
            "scan_run_count": count_value(scan_counts["total"]),
            "failed_scan_count": count_value(scan_counts["failed"]),
            "source_location_count": int(source_location_count),
            "coverage_assessment_count": int(coverage_assessment_count),
            "runtime_finding_count": int(runtime_finding_count),
        }
