# Changelog

All notable changes to `ruleatlas-demo` are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project uses semantic versioning.
The version is sourced from `src/ruleatlas_demo/version.py`.

## [0.1.0] - 2026-07-16

### Added
- Package scaffold (initialized and importable) with publishable metadata.

### Notes
- The demo/seed code intentionally remains in `apps/api`: it is the leaf composition layer that orchestrates
  every context (including app-tier ai/pipeline orchestrators), and nothing depends on it, so extracting it
  into a package would create a package→app cycle with no reuse benefit.
