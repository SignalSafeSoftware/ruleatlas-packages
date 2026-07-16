"""RuleAtlas demo / seed data generators (development only).

The current backend carries ~5k LOC of demo and seed generators (invoice analysis, demo AI providers, the
seed orchestrator, demo auth). That is a large, non-runtime slice mixed into the core package. Isolating it
here immediately shrinks the production surface: this package depends on everything, but **nothing depends
on it**, and it is intended to be installed only as an optional dev/demo extra of ``apps/api`` — never in a
production image.

Boundary: this is the one package allowed to import all the others. Guard it in the opposite direction — no
runtime package may import ``ruleatlas_demo``.

Status: SCAFFOLD. See ``README.md`` and ``docs/architecture/package-decomposition.md``.
"""

from __future__ import annotations

from ruleatlas_demo.version import __version__

__all__: list[str] = ["__version__"]
