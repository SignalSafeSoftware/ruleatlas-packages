"""Typed sqlPhilosophy repositories — one repository class per module.

Import ``RepositoryFactory`` from this package. Import specific repository or
query-builder classes from their modules.
"""

from ruleatlas_persistence.repositories.factory import RepositoryFactory

__all__ = [
    "RepositoryFactory",
]
