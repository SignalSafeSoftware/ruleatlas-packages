"""CSV formula-injection neutralization for exported cells (RA-08-002).

Spreadsheet apps (Excel/Sheets) execute cell content beginning with a formula trigger
(`= + - @`, tab, or CR). Scanned file paths, source-location names, override patterns, and
rule/claim text are attacker/user-controlled, so every exported cell is neutralized here.
"""

from __future__ import annotations

__all__ = ["sanitize_csv_cell"]

_DANGEROUS_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def sanitize_csv_cell(value: object) -> str:
    """Return a CSV-safe string; prefix formula-trigger leading chars with a single quote."""
    if value is None:
        return ""
    text = str(value)
    if text and text[0] in _DANGEROUS_PREFIXES:
        return "'" + text
    return text
