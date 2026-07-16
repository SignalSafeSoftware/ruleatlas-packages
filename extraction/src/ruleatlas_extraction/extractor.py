from __future__ import annotations

from typing import Protocol

from ruleatlas_persistence.models import SourceFile

from ruleatlas_extraction.schemas import ExtractionCandidate


class RuleExtractor(Protocol):
    def extract(self, source_file: SourceFile, text: str) -> list[ExtractionCandidate]:
        """Return candidate rules for a source file. Empty list means no candidates."""
