"""Pure candidate/rule classification shared by extraction and claims (breakup Phase 2).

scaffold detection + rule categorization/display. Depends only on the kernel enums; no DB/IO. Lives in
the kernel so both the extraction and claims contexts use it without importing each other.
"""
