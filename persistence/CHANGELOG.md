# Changelog

All notable changes to `ruleatlas-persistence` are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project uses semantic versioning.
The version is sourced from `src/ruleatlas_persistence/version.py`.

## [0.1.0] - 2026-07-16

### Added
- Initial extraction of the ORM ring from the `apps/api` backend.
- Declarative `Base`, `mixins`, and `enum_column` helpers.
- All ORM models (85 tables): `models/` (`core`, `scanning`, `rules`, `ai`, `graph_claims`, `tickets`).
- Append-only audit event listeners (`append_only`) and the `inventory_keyword` query helper.
- All ~55 `sqlphilosophy` repositories + `RepositoryFactory` (`repositories/`).
- `audit` dependency-inversion port (`record_audit_event` / `set_audit_recorder`) so context packages record
  audit without importing the app; the app registers the request-scoped recorder.

### Notes
- Depends on `ruleatlas-contracts`, SQLAlchemy, and `sqlphilosophy` (pinned `<0.2.0` to match `apps/api`).
- Engine/session wiring stays in `apps/api` (needs application configuration).
