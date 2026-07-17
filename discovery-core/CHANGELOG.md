# Changelog

All notable changes to `ruleatlas-discovery` are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project uses semantic versioning.
The version is sourced from `src/ruleatlas_discovery/version.py`.

## [0.1.0] - 2026-07-16

### Added
- File typing, built-in mappings, globbing, line counts, inventory metrics, directory tree, and DTO
  serialization for discovery.
- Scanning utilities extracted from `apps/api`: `file_type_registry`, `line_metrics`, `production_bucket`,
  `classification_signals`, `source_path_display`, `analyzer_sandbox`.

### Changed
- Added a `ruleatlas-contracts` dependency (kernel enums) and a mypy-strict gate; fixed the pre-existing
  serialization/metrics type gaps this surfaced.
