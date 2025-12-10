## Aria TOC-less Parsing – Strategy Snapshot

This file captures the latest decisions and near-term actions. See `parser_overview.md` for the full plan and `parser_experiments.md` for detailed logs.

### Current stance
- **Docling**: Preferred baseline; reliable Markdown chunks; tune `DOCLING_MAX_TOKEN_PER_CHUNK` per corpus.
- **Sherpa passthrough**: Promising for clause metadata but needs block→Markdown reconstruction and better handling of large PDFs (504 risk; no page slicing yet).
- **Sherpa `/parsing/` wrapper**: Not used (truncates early).
- **GPT-5 vision**: Comparison/fallback; slower but keeps layout text when other parsers fail.

### Immediate actions
1. Confirm Sherpa passthrough timeout/async options with CBAI; if none, test lighter `LLMSHERPA_QUERY` variants on large PDFs.
2. Finish block→Markdown/chunk reconstruction for Sherpa payloads and benchmark against Docling on Alliade + Vinci.
3. Run stabilized configs across ~10 contracts; export coverage CSVs and clause-aware chunks.
4. Summarize parser selection rules (default vs fallback) and draft comparison slides for handoff.
