# Changelog

All notable changes to `ruleatlas-ai` are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project uses semantic versioning.
The version is sourced from `src/ruleatlas_ai/version.py`.

## [0.1.0] - 2026-07-16

### Added
- Pure AI domain extracted from `apps/api`: `budget`; `providers/` (probe parsing/diagnostics/payloads/
  sanitization, `protocols`, `credential_validation`, `connection_errors`, `recommendations`); `synthesis/`
  (`schema`, `proposal_validation`, `synthesis_wording`, `wording_normalize`).

### Notes
- Depends on `ruleatlas-contracts`, `ruleatlas-claims`, `ruleatlas-persistence`, `pydantic`, `httpx`.
- Provider adapters, governance, connection/catalog/compatibility services, and the synthesis workflow remain
  in `apps/api` (they wire providers, config, and the request-scoped service factory).
