from types import SimpleNamespace
from unittest.mock import Mock, patch

from ruleatlas_claims.rules.rule_deduplication import (
    find_duplicate_groups,
    find_duplicate_groups_for_rule,
)


def _rule(rule_id: str, name: str, version_id: str) -> SimpleNamespace:
    return SimpleNamespace(id=rule_id, name=name, current_version_id=version_id)


def _repositories(rules: list[SimpleNamespace], texts: dict[str, str]) -> Mock:
    repositories = Mock()
    repositories.rules.return_value.list_for_dedup_candidates.return_value = rules
    repositories.rule_versions.return_value.map_by_ids.return_value = {
        version_id: SimpleNamespace(business_rule=text)
        for version_id, text in texts.items()
    }
    return repositories


def test_project_duplicate_groups_bulk_load_rule_versions_once() -> None:
    rules = [
        _rule("one", "First", "v1"),
        _rule("two", "Second", "v2"),
        _rule("three", "Third", "v3"),
    ]
    repositories = _repositories(
        rules,
        {
            "v1": "Administrators must retain audit records",
            "v2": "Administrators must retain audit record",
            "v3": "Customers may update their profile",
        },
    )

    with patch(
        "ruleatlas_claims.rules.rule_deduplication.RepositoryFactory",
        return_value=repositories,
    ):
        groups = find_duplicate_groups(Mock(), "project", min_similarity=0.5)

    assert [group.rule_ids for group in groups] == [["one", "two"]]
    repositories.rule_versions.return_value.map_by_ids.assert_called_once_with({"v1", "v2", "v3"})


def test_rule_scoped_duplicate_groups_compare_only_requested_rule() -> None:
    rules = [
        _rule("one", "First", "v1"),
        _rule("two", "Second", "v2"),
        _rule("three", "Third", "v3"),
    ]
    repositories = _repositories(
        rules,
        {
            "v1": "Administrators must retain audit records",
            "v2": "Administrators must retain audit record",
            "v3": "Customers may update their profile",
        },
    )

    with patch(
        "ruleatlas_claims.rules.rule_deduplication.RepositoryFactory",
        return_value=repositories,
    ):
        groups = find_duplicate_groups_for_rule(Mock(), "project", "two", min_similarity=0.5)

    assert len(groups) == 1
    assert groups[0].primary_rule_id == "two"
    assert groups[0].rule_ids == ["two", "one"]


def test_rule_scoped_duplicate_groups_return_empty_for_unknown_rule() -> None:
    repositories = _repositories([_rule("one", "First", "v1")], {"v1": "A rule"})

    with patch(
        "ruleatlas_claims.rules.rule_deduplication.RepositoryFactory",
        return_value=repositories,
    ):
        groups = find_duplicate_groups_for_rule(Mock(), "project", "missing")

    assert groups == []
    repositories.rule_versions.return_value.map_by_ids.assert_not_called()
