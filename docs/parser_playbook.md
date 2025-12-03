## Aria Contract Parsing Playbook

### 1. Mission Context
- **Client**: Vinci Construction legal (Aria web app).
- **Goal**: Help jurists assess large “appel d’offres” contracts (50–200+ pages) by answering 40 predefined questions grouped into 10 risk themes.
- **Current workflow**: Upload a single PDF → RAG pipeline parses and chunks → retrieval answers each question, citing page/chunk, and assigns a risk score per theme from a curated knowledge base. If evidence is missing the model flags it for manual review. A chat interface allows follow‑up Q&A.

### 2. New Feature Focus (Parsing Without TOC)
We are evaluating parsing approaches that preserve structural semantics even when the document lacks a clean table of contents.

| Feature Track | Description | Ownership |
| --- | --- | --- |
| **F1 – Structure‑aware parsing** | Compare Docling (via CBAI), LLM Sherpa (via CBAI passthrough), and fallback LLM parsing with images. Deliver state-of-the-art review, code to convert PDF→Markdown + chunking, and parsing metrics over 10 contracts. **You** |
| F2 – Chunk metadata + multi-doc flow | Enrich vector store with chunk provenance, test multi-doc promptflow pipeline (processing/retrieval/generation). | teammate |
| F3 – Contradiction handling in generation | Make prompts explicit about conflicting evidence across documents (CCAP/AE/RC first, then CCAG/CCAP). Includes design workshops + prompt implementation. | future effort |

This playbook tracks **F1**.

### 3. Data & Test Corpus
- Primary PDF: `data/reseau ASF.pdf` (97 pages, CCAP sample with POC).
- Additional contracts: target set of 10 (TBD) covering CCAP/AE/RC and CCAG variants once baseline stabilized.
- Storage: Keep raw PDFs under `data/` (ignored by Git).

### 4. Environment & Tooling
- Python 3.11, managed via `uv`.
- Key dependencies: `requests`, `python-dotenv`.
- CLI entry points:
  - `src/test_parsing.py` – Docling runner (async `/start-parsing/` + polling `/result-parsing/{task_id}`).
  - `src/llmsherpa_parsing.py` – LLM Sherpa runner (supports `/parsing/` and `/passthrough/api/parseDocument`).
- Shared helpers:
  - `src/env_utils.py` – `.env` loader & sanitized getters.
  - `src/result_exporter.py` – saves JSON payloads to `data/results/` and appends rows to `data/results/metrics.csv`.

### 5. Configuration
Set variables in `.env` (copy `.env.example` as base). Key knobs:

| Variable | Purpose |
| --- | --- |
| `DOCLING_ENV` (`TST`/`PPD`/`PRD`) | Selects built-in CBAI endpoint + API key. |
| `DOCLING_URL`, `DOCLING_API_KEY_VAR` | Optional override for custom hosts/keys. |
| `DOCLING_PDF_PATH` | PDF under test. |
| `DOCLING_EXPORT_TYPE`, `DOCLING_CHUNKING_TYPE`, `DOCLING_MAX_TOKEN_PER_CHUNK` | Controls Docling output (currently 1 500 tokens/chunk). |
| `DOCLING_POLL_INTERVAL`, `DOCLING_POLL_ATTEMPTS` | Poll cadence for async completion. |
| `LLMSHERPA_ENV` + `LLMSHERPA_URL` | CBAI environment + optional override. |
| `LLMSHERPA_ENDPOINT` | `parsing/` for default, `passthrough/api/parseDocument` for full Sherpa API. |
| `LLMSHERPA_QUERY` | URL-encoded params (e.g., `renderFormat=all&strategy=chunks&applyOcr=yes`). |
| `LLMSHERPA_PDF_PATH`, `LLMSHERPA_*` chunking knobs | Mirror Docling path and chunk size preferences. |
| `RUN_LABEL`, `RUN_NOTES` | Identifiers stored in filenames and `metrics.csv`. Use descriptive values per experiment (`docling-1500-vs-sherpa`, `sherpa-passthrough-tune-1`, etc.). |

### 6. Running Experiments
1. Set `RUN_LABEL` / `RUN_NOTES`.
2. Execute Docling or Sherpa CLI via `uv run python src/<cli>.py`.
3. Outputs:
   - JSON payload: `data/results/<parser>_<pdf>_<timestamp>_{RUN_LABEL}.json`.
   - Metrics row appended to `data/results/metrics.csv` with columns `[timestamp, experiment, parser, parser_env, pdf_path, status, duration_seconds, chunk_count, execution_time, notes]`.
4. Review `metrics.csv` to compare run duration (wall clock) vs `execution_time` (service-side processing), chunk counts, parser env, and notes.

### 7. Experiment Log (F1)

| Date (UTC) | RUN_LABEL | Parser | Env | Key Settings | Duration (s) | Exec Time (s) | Chunk Count | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2025-12-03 | `docling-7500-default` | Docling | TST/PPD/PRD | `max_chunk=7500` | 627 / 538 / 408 / 468 | 293–456 | 235 | Full coverage, but chunks too large for embeddings. |
| 2025-12-03 | `docling-1500-vs-sherpa` | Docling | PRD | `max_chunk=1500` | 397 | 387 | 240 | Balanced chunking; Markdown output. |
| 2025-12-03 | `docling-1500-vs-sherpa` | LLM Sherpa | PRD (`parsing/`) | `chunk_size=800`, default params | 9 | — | 73 (many empty bullets) | Coverage poor, truncated after early pages. |
| 2025-12-03 | `baseline-docling-1500-vs-sherpa-passthrough` | LLM Sherpa | PRD (`passthrough/api/parseDocument`) | `renderFormat=all&strategy=chunks&applyOcr=yes&useNewIndentParser=yes`, timeout 480s | 244 (timed out) | — | 0 | CBAI gateway returned 504 after 4 min; need async workflow or lighter params. |

> Update the table after each run. Include links to payloads (relative paths) when useful.

### 8. Observations (to date)
- **Docling** reliably extracts entire contracts even without a TOC and provides chunk metadata (page number, token estimate). Need to tune `max_token_per_chunk` and possibly `chunking_type` to balance context size and retrieval precision.
- **LLM Sherpa (default `/parsing/`)** returned structured HTML chunks but dropped significant content beyond the first pages. Hypothesis: default params (no OCR, limited render format) or CBAI wrapper constraints caused truncation.
- **LLM Sherpa passthrough** attempt (full render + OCR) hit a 504 Gateway Timeout after ~4 minutes → need larger timeout and/or asynchronous pattern or lighter parameter set.
- Metrics show Docling’s end-to-end latency varies by environment; PRD currently fastest wall-clock despite higher reported execution time.

### 9. Next Steps
1. Complete Sherpa passthrough experiment(s); coordinate with CBAI to confirm whether a start/result async flow exists or if payload must stay synchronous (current settings return 504 after 4 min). If async is available, mirror Docling’s polling pattern.
2. If synchronous-only, test variations: (a) disable OCR or `renderFormat=all`, (b) reduce page count (split PDF) to gauge capacity, (c) adjust chunk/token parameters. Log each attempt via `RUN_LABEL`.
3. Run the validated parser configs across ~10 contracts. Use consistent labels per document (`docling-1500-contract02`, `sherpa-passthrough-contract02`, etc.).
4. Build parsing quality metrics (percent of pages covered, non-empty chunk rate, avg tokens/chunk). Consider a notebook that reads `data/results/*.json` and visualizes coverage.
5. Prepare comparison slides summarizing latency, API cost estimates, parsing fidelity, and final parser recommendation for the Aria RAG pipeline.
6. Feed the chosen parser pipeline into Promptflow (PDF → Markdown + chunk metadata) once the evaluation is complete.

### 10. Open TODOs
1. **Log passthrough failure** – ✅ captured 504 run in `metrics.csv` with `RUN_LABEL=baseline-docling-1500-vs-sherpa-passthrough`.
2. **Consult CBAI/Sherpa team** about async access or timeout limits for `/passthrough/api/parseDocument`.
3. **Experiment with parameter subsets** (e.g., `renderFormat=text`, `applyOcr=no`, smaller PDFs) to find a viable synchronous configuration.
4. **Automate metrics ingestion**: add script/notebook summarizing coverage/missing chunks for each run.
5. **Expand corpus** once Sherpa path stabilizes; schedule batch runs on the 10 target contracts.

### 11. Master Plan (Feature 1 – TOC-less Parsing)

**Phase 1 – Baseline & Metrics (in progress)**  
- Keep executing controlled Docling/Sherpa runs with clear `RUN_LABEL`s, saving payloads + metrics.  
- Build coverage metrics (e.g., % of pages covered, non-empty chunk rate) so “structure preserved” becomes measurable.  
- Capture failures (timeouts, truncated chunks) just like successes to understand each parser’s limits.

**Phase 2 – Parser Optimization**  
- Docling: tune `max_token_per_chunk`, chunking strategy, OCR flags to ensure headings/sections remain intact even when no TOC exists.  
- Sherpa: unblock passthrough (async or parameter tweaks) and find parameter sets that return within the timeout while keeping layout fidelity.  
- Document each iteration (what changed, how coverage/latency shifted).

**Phase 3 – Comparative Evaluation**  
- Once both parsers produce usable chunks, run them across ~10 representative contracts (CCAP/AE/RC and CCAG).  
- For each run, log time, chunk stats, coverage metrics, and a few sample chunks for manual spot checks.  
- Use this data to populate the comparison slides (time, cost, performance) and define parser selection rules (e.g., Docling default, Sherpa for heavy-layout annexes).

**Phase 4 – Integration & Feedback**  
- Feed the selected parser configuration into Promptflow (PDF → Markdown + chunk metadata) so downstream RAG steps can rely on consistent structure even without a TOC.  
- Share learnings with the team (slides, docs) and keep the playbook + TODO list updated so the next engineer/agent can continue the loop.  
- Once Feature 1 stabilizes, move to the other feature tracks (multi-doc metadata, contradiction handling) using the same logging discipline.

### 10. References
- **Aria**: internal RAG app for legal risk assessment (40 questions / 10 themes).
- **Docling API**: `/start-parsing/` + `/result-parsing/{task_id}` endpoints exposed via CBAI (TST/PPD/PRD).
- **LLM Sherpa API**: `/parsing/` wrapper and `/passthrough/api/parseDocument` for direct access (docs: https://llmsherpa.readthedocs.io).

Keep this playbook updated after each experiment so future agents or teammates can jump in with full context.
