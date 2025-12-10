## Aria TOC-less Parsing Playground

Tools and experiment logs for evaluating structure-aware PDF parsing when contracts lack a clean table of contents. We compare Docling, LLM Sherpa passthrough, and a GPT-5 fallback, export their payloads, and compute coverage/chunking metrics for Aria’s 40-question legal RAG workflow.

### Prerequisites
- Python 3.11
- [`uv`](https://github.com/astral-sh/uv) for dependency and runner tooling

### Setup
1. Install deps: `uv sync` (or `uv pip install -r pyproject.toml`).
2. Copy `.env.example` → `.env` and fill keys + parser settings. At minimum set:
   - `CBAI_API_KEY_TST` / `CBAI_API_KEY_PPD` / `CBAI_API_KEY_PRD`
   - `DOCLING_ENV`, `DOCLING_PDF_PATH`
   - `LLMSHERPA_ENV`, `LLMSHERPA_PDF_PATH`
   - `RUN_LABEL` / `RUN_NOTES` for clean filenames and metrics rows

### Key environment variables
- **Docling**: `DOCLING_ENV`, `DOCLING_URL`, `DOCLING_API_KEY_VAR`, `DOCLING_PDF_PATH`, `DOCLING_EXPORT_TYPE`, `DOCLING_CHUNKING_TYPE`, `DOCLING_MAX_TOKEN_PER_CHUNK`, `DOCLING_POLL_INTERVAL`, `DOCLING_POLL_ATTEMPTS`.
- **LLM Sherpa**: `LLMSHERPA_ENV`, `LLMSHERPA_URL`, `LLMSHERPA_API_KEY_VAR`, `LLMSHERPA_ENDPOINT` (`parsing/` vs `passthrough/api/parseDocument`), `LLMSHERPA_QUERY` (e.g., `renderFormat=all&strategy=chunks&applyOcr=yes`), `LLMSHERPA_PDF_PATH`, `LLMSHERPA_CHUNK_SIZE`, `LLMSHERPA_CHUNK_OVERLAP`, `LLMSHERPA_TIMEOUT`.
- **GPT-5 vision parser**: `GPT_PARSER_PDF_PATH`, `GPT_PARSER_IMAGE_DESCRIPTION`, `GPT_PARSER_EXTRA_INSTRUCTION`, plus `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_GPT5_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION`.
- **Experiment labels**: `RUN_LABEL`, `RUN_NOTES` are recorded in filenames and `metrics.csv`.

### CLI entry points (via `uv run python -m ...`)
- `parsing_tests.cli.docling_runner` – Docling start/poll flow; saves JSON and appends metrics.
- `parsing_tests.cli.llmsherpa_runner` – Sherpa wrapper or passthrough call; supports full render + OCR via `LLMSHERPA_QUERY`.
- `parsing_tests.cli.gpt_runner` – GPT-5 vision parsing through Azure OpenAI; emits one Markdown chunk per page.
- `parsing_tests.cli.remove_toc` – clones a PDF without its TOC for TOC-less benchmarks.
- `parsing_tests.analysis.coverage_cli` – computes coverage CSVs from saved payloads.
- `parsing_tests.analysis.clause_chunker` – converts Docling/Sherpa/GPT payloads into clause-aware chunks with inherited metadata.

### Data & outputs
- PDFs live under `data/` (gitignored). Primary sample: `data/reseau ASF.pdf`; Alliade and Vinci samples used in experiments.
- Parser payloads: `data/results/<parser>_<pdf>_<timestamp>_{RUN_LABEL}.json`.
- Metrics log: `data/results/metrics.csv` with timestamp, parser, env, duration, exec time, chunk count, notes.
- Coverage exports: run `coverage_cli` to produce comparison CSVs; clause-aware chunks sit next to their source payloads.

### Current findings
- Docling reliably parses full contracts (TOC or not) and outputs Markdown chunks; tuning `DOCLING_MAX_TOKEN_PER_CHUNK` balances latency vs retrieval fidelity.
- Sherpa default `/parsing/` truncates early; passthrough with `renderFormat=all&strategy=chunks&applyOcr=yes` completes quickly on medium PDFs and exposes clause metadata but can time out (504) on larger files.
- Clause-aware chunking is being built on top of Sherpa/Docling payloads to preserve section boundaries through downstream chunk splits.
- GPT-5 vision runner is available as a fallback/parser comparison; use `clause_chunker` to align its output with other parsers.

### Documentation map
- `docs/parser_overview.md` – mission, scope, corpus, tooling, config.
- `docs/parser_playbook.md` – feature plan and process at a glance.
- `docs/parser_experiments.md` – run history, coverage snapshots, Sherpa/Vinci notes.
- `docs/parser_strategy.md` – observations, next steps, master plan.
- `docs/parser_clause_comparison.md` – clause-aware chunking rationale.
- `docs/todo.md`, `docs/weekly_updates_*.md`, `docs/progress_*.md` – backlog and progress logs.

### Troubleshooting tips
- Auth: ensure env keys match the target endpoint; override `*_API_KEY_VAR` if using non-CBAI vars.
- Long runs/timeouts: raise `DOCLING_POLL_ATTEMPTS`/`INTERVAL`; for Sherpa passthrough, try lighter `LLMSHERPA_QUERY` or smaller PDFs if you hit 504s.
- Output coverage: run `coverage_cli` against saved payloads to verify page coverage and chunk counts before RAG retrieval tests.
