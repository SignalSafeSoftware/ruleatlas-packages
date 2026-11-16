# Changelog

## Publisher maintenance — 2026-11-15

- Replace an unavailable publisher action pin with verified v1.14.3, including current metadata validation for the build backend’s Metadata-Version 2.5.
- Permit a fully gated retry of an existing immutable package tag; retain exact-tag version validation and all workspace checks. No package runtime or version changes.

## Coordinated 0.1.1 / discovery 0.1.2 — 2026-11-15

- Reconcile the eight reviewed dependency/action updates and regenerate the real uv workspace lock.
- Align internal package minimums and source versions for the coordinated release; preserve domain boundaries and existing runtime exports.
- Refresh release-state documentation; no PyPI publication or host deployment is implied by source preparation.
