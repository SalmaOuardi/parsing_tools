## Aria TOC-less Parsing – Overview

One-stop view of the mission, tooling, and plan for Feature 1 (structure-aware parsing without TOCs).

### 1. Mission & scope
- Keep Aria’s 40-question legal RAG flow working even when contracts have no table of contents.
- Pipeline: PDF → parser → Markdown chunks with metadata → retrieval/generation with citations.
- Tracks (F1-F3): F1 = parser evaluation (this doc), F2 = chunk metadata + multi-doc orchestration, F3 = contradiction handling.

### 2. Corpus
- Primary sample: `data/reseau ASF.pdf` (97-page CCAP).
- Additional samples: Alliade and Vinci PDFs; target set of ~10 contracts across CCAP/AE/RC and CCAG once configs stabilize.
- TOC-less variants: create with `uv run python -m parsing_tests.cli.remove_toc --pages <range>`; keep originals under `data/` (gitignored).

### 3. Tooling & entry points
- Python 3.11 via `uv`.
- Runners: `parsing_tests/cli/docling_runner.py`, `parsing_tests/cli/llmsherpa_runner.py`, `parsing_tests/cli/gpt_runner.py`.
- Utilities: `parsing_tests/utils/env.py`, `parsing_tests/utils/result_exporter.py`, `parsing_tests/cli/remove_toc.py`.
- Analysis: `parsing_tests/analysis/coverage_cli.py`, `parsing_tests/analysis/clause_chunker.py`, `parsing_tests/analysis/clause_compare.py`, `parsing_tests/analysis/clause_preview.py`.

### 4. Configuration (set in `.env`)
- **Docling**: `DOCLING_ENV`, `DOCLING_URL`, `DOCLING_API_KEY_VAR`, `DOCLING_PDF_PATH`, `DOCLING_EXPORT_TYPE`, `DOCLING_CHUNKING_TYPE`, `DOCLING_MAX_TOKEN_PER_CHUNK`, `DOCLING_POLL_INTERVAL`, `DOCLING_POLL_ATTEMPTS`.
- **LLM Sherpa**: `LLMSHERPA_ENV`, `LLMSHERPA_URL`, `LLMSHERPA_API_KEY_VAR`, `LLMSHERPA_ENDPOINT` (`parsing/` or `passthrough/api/parseDocument`), `LLMSHERPA_QUERY` (e.g., `renderFormat=all&strategy=chunks&applyOcr=yes`), `LLMSHERPA_PDF_PATH`, `LLMSHERPA_CHUNK_SIZE`, `LLMSHERPA_CHUNK_OVERLAP`, `LLMSHERPA_TIMEOUT`.
- **GPT-5 vision**: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_GPT5_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION`, plus `GPT_PARSER_PDF_PATH`, `GPT_PARSER_IMAGE_DESCRIPTION`, `GPT_PARSER_EXTRA_INSTRUCTION`.
- **Experiment labels**: `RUN_LABEL`, `RUN_NOTES` (used in filenames and `metrics.csv`).

### 5. Experiment workflow
1. Set `RUN_LABEL` / `RUN_NOTES` + parser-specific env vars.
2. Run a parser: `uv run python -m parsing_tests.cli.<docling_runner|llmsherpa_runner|gpt_runner>`.
3. Outputs:
   - Payload: `data/results/<parser>/<pdf_slug>/<timestamp>_{RUN_LABEL}.json` (or legacy flat format).
   - Metrics row: `data/results/metrics.csv` with timestamp, parser, env, duration, exec time, chunk count, notes.
4. Coverage: `uv run python -m parsing_tests.analysis.coverage_cli --config <json> --out-csv <csv>`.
5. Clause-aware chunks: `uv run python -m parsing_tests.analysis.clause_chunker --parser <docling|sherpa|gpt> --file <payload> --out <path>`.

### 6. Current status (F1)
- Docling: reliable Markdown chunks; main knob is `DOCLING_MAX_TOKEN_PER_CHUNK` to balance latency vs retrieval precision.
- Sherpa:
  - `parsing/` wrapper truncates after early pages (not used).
  - Passthrough with `renderFormat=all&strategy=chunks&applyOcr=yes` returns full layout blocks quickly on medium PDFs and exposes clause boundaries but can 504 on larger files; lacks page slicing.
- GPT-5 vision: available as comparison/fallback; emits one Markdown chunk per page; slower than Docling.
- Clause-aware chunking: `clause_chunker` rebuilds chunk-level clause metadata for Docling/Sherpa/GPT payloads; see `parser_clause_comparison.md` for rationale.
- Metrics/coverage: `parser_experiments.md` holds run history, coverage snapshots, and Sherpa reliability notes.

### 7. Next steps (working list for F1)
1. Confirm Sherpa passthrough async/timeouts with CBAI or find lighter params for large PDFs.
2. Finish block → Markdown/chunk reconstruction for Sherpa passthrough payloads and benchmark against Docling.
3. Run the stabilized configs across ~10 contracts with consistent `RUN_LABEL`s; export coverage CSVs.
4. Analyze clause coverage and annex gaps; decide parser selection rules.
5. Prepare comparison slides (latency, coverage, cost) and hand off the chosen parser into Promptflow.

### 8. Phase plan (F1)
- **Baseline & metrics**: keep labeled runs + metrics; log failures.
- **Parser optimization**: Docling chunk tuning; Sherpa passthrough tuning/async; clause-aware reconstruction.
- **Comparative eval**: 10-contract batch with coverage + sample chunks.
- **Integration**: plug the chosen parser into Promptflow; reuse chunk metadata for multi-doc work (F2) and contradiction prompts (F3).
