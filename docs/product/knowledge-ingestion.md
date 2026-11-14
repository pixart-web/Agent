# Safe knowledge ingestion

Knowledge accepts UTF-8 TXT/Markdown, PDF, and DOCX documents up to 5 MB. PDF extraction is
limited to 200 pages. DOCX archives are rejected when encrypted, excessively expanded, or made
of too many embedded files. Macros and arbitrary formats are not accepted, and no uploaded
binary is executed or retained.

Only normalized text (maximum 100,000 characters), a SHA-256 fingerprint, the safe filename,
format, byte count, and extractor version are stored. Duplicate active documents in a workspace
are rejected. Every import begins as a draft and remains absent from search until an owner or
admin approves it.

Retrieval is tenant scoped, sensitivity filtered, approval gated, and provenance bearing. Its
results are explicitly labelled untrusted reference data rather than executable instructions.
Archival is non-destructive and removes an item from listing and retrieval without destroying its
revision history.
