# Changelog

All notable changes to `ruleatlas-extraction` are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project uses semantic versioning.
The version is sourced from `src/ruleatlas_extraction/version.py`.

## [0.1.0] - 2026-07-16

### Added
- Pure candidate-extraction domain extracted from `apps/api`: `heuristic_extractor`, `comment_classifier`,
  `extractor`, `schemas`, and BDD extractors (`bdd/`: `bdd_claims`, `gherkin_ingestion`, `step_linking`).

### Notes
- Depends on `ruleatlas-contracts`, `ruleatlas-discovery`, `ruleatlas-persistence`, `pydantic`, `gherkin-official`.
- File-reading/pipeline orchestrators (`service`, `file_reader`, `rule_writer`) remain in `apps/api`.
