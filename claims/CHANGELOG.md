# Changelog

All notable changes to `ruleatlas-claims` are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project uses semantic versioning.
The version is sourced from `src/ruleatlas_claims/version.py`.

## [0.1.0] - 2026-07-16

### Added
- Pure rule-IR domain extracted from `apps/api`: `claim_service`, `structured_semantics`, `clustering/`
  (`canonicalize`, `cluster_roles`, `cluster_attachments`, `cluster_service`), `conflicts/`, `gaps/`,
  `rules/` (`reclassify`, `rule_deduplication`, `rule_version_queries`, `rule_identity`), `graph/`, `semantic/`.
- Model-free helpers: `confidence_scorer`, `relationship_suggester`, `text_normalize`.

### Notes
- Depends on `ruleatlas-contracts` + `ruleatlas-persistence`. Audit is recorded via the persistence audit port.
- Audit/service-factory orchestrators remain in `apps/api` (they resolve request-scoped actors / wire services).
