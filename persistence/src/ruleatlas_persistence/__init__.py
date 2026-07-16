"""RuleAtlas persistence layer: SQLAlchemy ORM models + repositories.

The database ring of the architecture. It owns the SQLAlchemy declarative ``Base``, all ORM models, the
column/mixin helpers, and the ``sqlphilosophy``-based repositories that every other context uses to read and
write data. It exists so that context packages (``claims``, ``ai``, ``extraction``, ``exports``, ``demo``,
``discovery``) can depend on *one* shared persistence package instead of reaching back into ``apps/api``.

What lives here: models, repositories, ``Base``, mixins, ``enum_column`` helpers, and the append-only audit
listeners. What does NOT: the engine/``SessionLocal`` wiring (needs app configuration, so it stays in
``apps/api``), business logic, services, and API routes.

Boundary: depends only on ``ruleatlas-contracts`` (enums/value objects) + SQLAlchemy + sqlphilosophy. It must
never import an application/api module — that back-edge is what would make the DAG cyclic.

Status: SCAFFOLD — initialized and importable; the ORM layer migrates in next (see ``README.md`` and
``docs/architecture/package-decomposition.md``).
"""

from __future__ import annotations

from ruleatlas_persistence.version import __version__

__all__: list[str] = ["__version__"]
