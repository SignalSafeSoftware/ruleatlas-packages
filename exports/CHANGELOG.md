# Changelog

All notable changes to `ruleatlas-exports` are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project uses semantic versioning.
The version is sourced from `src/ruleatlas_exports/version.py`.

## [0.1.0] - 2026-07-16

### Added
- Pure export formatters extracted from `apps/api`: `csv_safety` (formula-injection neutralization),
  `export_labels`, `markdown_builder`, `report_types`.

### Notes
- Depends on `ruleatlas-contracts`. The report *builders* (which orchestrate app queries/scanning) remain in
  `apps/api` by design.
