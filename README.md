## PDF Parsing Playground

This repository contains CLI utilities for exploring document-parsing services (Docling and LLM Sherpa) as part of a retrieval-augmented generation (RAG) workflow. Each script sends a PDF to the respective service, handles authentication/polling, and logs the structured output so you can experiment locally without exposing private client infrastructure.

### Prerequisites

- Python 3.11.x
- [`uv`](https://github.com/astral-sh/uv) for dependency management

### Setup

1. Install dependencies:

   ```powershell
   uv pip install -r pyproject.toml
   ```

2. Create a `.env` file (based on `.env.example`) and add your API keys + runtime overrides. Example:

   ```dotenv
   CBAI_API_KEY_TST="..."
   CBAI_API_KEY_PPD="..."
   CBAI_API_KEY_PRD="..."

   DOCLING_ENV=TST
   DOCLING_PDF_PATH="data/reseau ASF.pdf"
   DOCLING_POLL_INTERVAL=10
   DOCLING_POLL_ATTEMPTS=120
   ```

### Environment Variables

| Variable | Description |
| --- | --- |
| `CBAI_API_KEY_TST` / `PPD` / `PRD` | Docling API keys for each environment. |
| `DOCLING_ENV` | Selects which built-in endpoint + key to use (`TST`, `PPD`, `PRD`). Defaults to `TST`. |
| `DOCLING_URL` | Optional override for the Docling base URL if you have a custom host. |
| `DOCLING_API_KEY_VAR` | Optional override to point at a different env var for the Docling key. |
| `DOCLING_PDF_PATH` | PDF path used by `test_parsing.py`. |
| `DOCLING_EXPORT_TYPE` | Docling export format (`markdown`, `json`). |
| `DOCLING_CHUNKING_TYPE` | Docling chunking strategy (`hybrid`, `none`, etc.). |
| `DOCLING_PICTURE_MODEL` | Optional Docling model for picture descriptions. |
| `DOCLING_PICTURE_PROMPT` | Picture description prompt. |
| `DOCLING_MAX_TOKEN_PER_CHUNK` | Integer cap for Docling chunk tokens. |
| `DOCLING_POLL_INTERVAL` | Seconds between Docling status checks. |
| `DOCLING_POLL_ATTEMPTS` | Number of Docling polls before timing out. |
| `LLMSHERPA_URL` | Base URL for your LLM Sherpa service (e.g., `https://llmsherpa.yourdomain/api`). |
| `LLMSHERPA_ENV` | Selects which CBAI endpoint to use for LLM Sherpa (`TST`, `PPD`, `PRD`). |
| `LLMSHERPA_URL` | Optional override for the base path (defaults to the env-specific `/cbai/v1/llm_sherpa`). |
| `LLMSHERPA_API_KEY_VAR` | Env var that stores the LLM Sherpa key (defaults to the matching `CBAI_API_KEY_*`). |
| `LLMSHERPA_ENDPOINT` | Relative endpoint appended to the base URL (`parsing/`, `passthrough/api/...`, etc.). |
| `LLMSHERPA_QUERY` | URL-encoded query string for additional Sherpa parameters (`renderFormat=all&applyOcr=no`). |
| `LLMSHERPA_PDF_PATH` | PDF path used by `llmsherpa_parsing.py`. |
| `LLMSHERPA_PRESERVE_LAYOUT` | `true/false` to keep layout metadata. |
| `LLMSHERPA_CHUNK_SIZE` | Chunk token size for Sherpa responses. |
| `LLMSHERPA_CHUNK_OVERLAP` | Token overlap between Sherpa chunks. |
| `LLMSHERPA_TIMEOUT` | Request timeout (seconds) for Sherpa calls. |
| `RUN_LABEL` / `RUN_NOTES` | Optional experiment identifiers recorded in filenames and `metrics.csv` for later analysis. |

### Run the Docling CLI

```powershell
uv run python src/test_parsing.py
```

Flow overview:

1. Selects the Docling environment (`DOCLING_URL` + key) and logs the current settings.
2. Uploads the PDF to `/start-parsing/`. If Docling finishes inline, the final payload is printed immediately.
3. Otherwise polls `/result-parsing/{task_id}` until completion or until the configured timeout is exceeded.
4. Logs the final JSON, including chunk metadata ready for downstream RAG steps.
5. Saves the full JSON response to `data/results/docling_<pdf>_<timestamp>.json` and appends metrics (duration, chunk count, etc.) to `data/results/metrics.csv`.

### Run the LLM Sherpa CLI

```powershell
uv run python src/llmsherpa_parsing.py
```

This script pushes the PDF (plus layout/chunking preferences) to an LLM Sherpa endpoint and prints back the structured response for quick inspection.
It also writes the payload under `data/results/llmsherpa_<pdf>_<timestamp>.json` and appends timing/metadata to the shared metrics CSV so you can compare parsers run-by-run.
Use `LLMSHERPA_ENV` (`TST`, `PPD`, `PRD`) to switch between CBAI environments, or provide a custom `LLMSHERPA_URL`/`LLMSHERPA_ENDPOINT` for passthrough calls (e.g., `/passthrough/api/parseDocument?renderFormat=all`).

### Tracking Experiments

- Every run stores the raw payload in `data/results/<parser>_<pdf>_<timestamp>_{RUN_LABEL}.json`.
- `data/results/metrics.csv` aggregates timings, chunk counts, environments, and notes for both parsers so you can pivot/sort later.
- Set `RUN_LABEL` for the experiment name (e.g., `docling-1500-vs-sherpa`) and `RUN_NOTES` for extra context (`"Docling chunk=1500 | Sherpa default"`). These values propagate to filenames and the metrics CSV.

### Troubleshooting

- **Auth errors**: Confirm your `*_API_KEY` matches the URL you’re calling and that the header/query format matches what your deployment expects.
- **Long PDFs**: Increase `DOCLING_POLL_INTERVAL`/`DOCLING_POLL_ATTEMPTS` or Sherpa chunk sizes for better throughput.
- **Different endpoints**: Override `DOCLING_URL` or `LLMSHERPA_URL` to point at staging/local servers without editing the source.

### Project Structure

- `src/test_parsing.py` – Docling helper CLI (async poll + settings builder).
- `src/llmsherpa_parsing.py` – LLM Sherpa helper CLI (synchronous extraction).
- `src/env_utils.py` – shared helpers for `.env` loading and key lookup.
- `data/` – sample PDFs (ignored from Git). Bring your own documents.
- `pyproject.toml` – dependency definitions managed by `uv`.

### Contributing

- Keep actual credentials in `.env`; share sanitized examples via `.env.example`.
- Use `uv` for dependency management and add tests/linters as the playground grows.
- Feel free to extend either CLI or add adapters for additional parsers in the RAG toolchain.
