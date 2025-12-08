## Aria TOC-less Parsing – Overview

### 1. Mission context
- Goal: keep Aria’s 40-question risk workflow working even when a contract has no clean TOC.
- Current flow: PDF → parser → Markdown chunks → RAG answers + citations → jurists review in chat.

### 2. Feature focus
| Track | Scope | Owner |
| --- | --- | --- |
| **F1 – Structure-aware parsing** | Docling vs LLM Sherpa passthrough vs GPT fallback; deliver code + metrics across ~10 contracts. | us |
| F2 – Chunk metadata & multi-doc | Promptflow orchestration with provenance. | teammate |
| F3 – Contradiction handling | Prompt updates for CCAP/AE/RC/CCAG conflicts. | future |

This doc covers F1.

### 3. Data & corpus
- Primary sample: `data/reseau ASF.pdf` (97 pages, CCAP).
- Build a 10-contract set (CCAP/AE/RC + CCAG) once parsers stabilize.
- Keep originals in `data/` (gitignored). Use `uv run python -m parsing_tests.cli.remove_toc` to clone TOC-less variants while preserving the reference copy.

### 4. Tooling
- Python 3.11 via `uv`.
- CLI runners:
  - `parsing_tests/cli/docling_runner.py` (Docling start/poll flow).
  - `parsing_tests/cli/llmsherpa_runner.py` (default wrapper or passthrough endpoint).
- Shared helpers:
  - `parsing_tests/utils/env.py` (env loading).
  - `parsing_tests/utils/result_exporter.py` (JSON export + metrics append).
  - `parsing_tests/cli/remove_toc.py` (TOC stripping).
  - `parsing_tests/analysis/coverage_cli.py` (coverage metrics from saved payloads).

### 5. Config knobs
Set these in `.env` (copy `.env.example` first):

| Variable | Notes |
| --- | --- |
| `DOCLING_ENV`, `DOCLING_URL`, `DOCLING_API_KEY_VAR` | Pick endpoint/key or override. |
| `DOCLING_PDF_PATH`, `DOCLING_EXPORT_TYPE`, `DOCLING_CHUNKING_TYPE`, `DOCLING_MAX_TOKEN_PER_CHUNK` | Control Docling source + chunk size (e.g., 1500). |
| `DOCLING_POLL_INTERVAL`, `DOCLING_POLL_ATTEMPTS` | Async polling cadence. |
| `LLMSHERPA_ENV`, `LLMSHERPA_URL`, `LLMSHERPA_API_KEY_VAR` | Same concept for Sherpa. |
| `LLMSHERPA_ENDPOINT`, `LLMSHERPA_QUERY` | Choose wrapper vs passthrough + params (`renderFormat=all&strategy=chunks…`). |
| `LLMSHERPA_PDF_PATH`, `LLMSHERPA_CHUNK_SIZE`, `LLMSHERPA_CHUNK_OVERLAP`, `LLMSHERPA_TIMEOUT` | Sherpa input + chunk tuneables. |
| `RUN_LABEL`, `RUN_NOTES` | Required for clean filenames and metrics rows. |

### 6. Running experiments
1. Set `RUN_LABEL` / `RUN_NOTES`.
2. Run the parser CLI via `uv run python -m parsing_tests.cli.<runner_name>`.
3. We automatically save:
   - Payload → `data/results/<parser>_<pdf>_<timestamp>_{RUN_LABEL}.json`.
   - Metrics row → `data/results/metrics.csv` (timestamp, parser, env, duration, chunk count, exec time, notes).
4. Use `uv run python -m parsing_tests.analysis.coverage_cli` to convert payloads into coverage CSVs for comparisons.
