# Changelog

All notable changes to `ruleatlas-contracts` are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project uses semantic versioning.
The version is sourced from `src/ruleatlas_contracts/version.py`.

## [0.1.0] - 2026-07-16

### Added
- Initial extraction of the shared kernel from the `apps/api` backend (dependency-free: stdlib only).
- Enums (`enums`), enum coercion helper (`enum_utils`), and DTOs including `ClaimDraft` (`claims`).
- Provider contracts: `graph_contract`, `semantic_contract`.
- Classification stack (`classification/`): scaffold detection (`scaffold_classify`, `scaffold_markers`,
  `scaffold_filter`), rule categorization/display (`rule_category`, `rule_display`), and override validation
  (`override_validation`).
- Authorization policy (`authorization`): role ranks, permission→role mapping, `permission_satisfied`.
