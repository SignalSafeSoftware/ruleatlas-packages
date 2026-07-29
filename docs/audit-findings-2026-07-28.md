# RuleAtlas Packages Audit Findings — 2026-07-28

## Verdict

**PASS — release-ready.** All eight packages pass the exact isolated `uv`
validation matrix, their distributions and installed examples were verified,
and publishing is now gated by validation, package-specific tag/version checks,
and commit-pinned workflow actions.

## Scope and evidence

- Branch at audit start: `main`, synchronized with `origin/main`
- Tracked inventory: 271 files, approximately 36,181 lines and 1.43 MB
- Workspace members audited: contracts, persistence, discovery-core, claims,
  extraction, exports, ai, and demo
- Test inventory: 35 tracked test modules
- No private cross-package imports found by the focused static search
- Import-linter result: one contract kept, zero broken; 194 files and 417
  dependencies analyzed

### Validation results

| Validation | Result |
|---|---|
| Exact `uv` CI commands | PASS for all eight packages |
| Ruff | PASS for all eight packages |
| Pytest | PASS — 229 tests across all eight packages |
| Cross-package import contract | PASS — 1 kept, 0 broken |
| Mypy exact package runs | PASS for all eight packages |
| Wheel and sdist builds | PASS — 16 artifacts; all pass `twine check` |
| Installed distribution smoke | PASS — fresh venv; README examples pass |
| Python dependency vulnerability scan | PASS — no known vulnerabilities |

## Findings

### RA-PKG-P1-001 — Release tags bypass package quality gates

**Severity:** P1  
**Status:** Verified fixed

**Evidence:** `.github/workflows/ci.yml` runs on branch pushes and pull
requests. `.github/workflows/release.yml` runs on `v*` tags but only checks out,
builds, and publishes each matrix member; it does not run Ruff, mypy, pytest, or
the import-linter contract.

**Impact:** A tag can publish packages from a commit that never passed the
package CI workflow, including a commit with a broken dependency DAG or tests.

**Remediation:** Add a required validation job to the release workflow (or call
a reusable CI workflow) and make every publish matrix job depend on it.

### RA-PKG-P2-002 — One generic tag attempts to publish every package

**Severity:** P2  
**Status:** Verified fixed

**Evidence:** `.github/workflows/release.yml` matches every `v*` tag and uses a
fixed eight-package matrix. Versions are read independently from each package's
`src/.../version.py`.

**Impact:** A tag intended for one package attempts to publish all packages.
Unchanged versions can cause partial publish failures, while independently
changed versions have no tag-to-artifact consistency check.

**Remediation:** Adopt and validate either a lockstep version/tag policy or
package-specific tags. Before publishing, verify tag/version agreement and
detect already-published artifacts.

### RA-PKG-P2-003 — Workflow dependencies are mutable tags

**Severity:** P2  
**Status:** Verified fixed

**Evidence:** CI and release workflows use mutable major tags such as
`actions/checkout@v7`, `astral-sh/setup-uv@v7`, and
`pypa/gh-action-pypi-publish@release/v1`.

**Impact:** A compromised or unexpectedly changed upstream tag can alter
build/release execution, including an OIDC-authorized publishing job.

**Remediation:** Pin third-party actions to reviewed commit SHAs and use
Dependabot to update those pins.

## Remediation verification

- Release validation now runs the complete eight-package matrix and the import
  contract before any publish job can start.
- Package-specific tags are validated against the selected package's source
  version, so one tag publishes exactly one matching distribution.
- Checkout, uv setup, and PyPI publication actions are pinned to reviewed commit
  SHAs.
- The exact matrix passes Ruff, mypy, 229 tests, builds all 16 wheel/sdist
  artifacts, keeps the import contract, and passes `twine check`.
- A clean environment installs the built wheels and executes the corrected
  README examples. The dependency scan reports no known vulnerabilities.

## Checklist

### Audit completion

- [x] Tracked inventory and all eight package scopes recorded
- [x] Public dependency direction reviewed
- [x] Focused suppression/dead-code/private-import searches completed
- [x] Supplemental Ruff and pytest results recorded
- [x] Import-linter contract recorded
- [x] CI and release workflows reviewed
- [x] Install `uv` and run all eight isolated sync/lint/type/test/build jobs
- [x] Inspect all built wheel/sdist contents
- [x] Run a Python dependency vulnerability scanner against `uv.lock`
- [x] Verify README and changelog examples against installed distributions

### Remediation

- [x] RA-PKG-P1-001: gate publish jobs on the complete package CI suite
- [x] RA-PKG-P2-002: enforce a coherent tag/version publication policy
- [x] RA-PKG-P2-003: pin workflow actions to commit SHAs
- [x] Rerun the exact CI matrix and update this verdict
