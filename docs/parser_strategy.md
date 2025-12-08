## Aria TOC-less Parsing – Strategy

### 8. Observations
- Docling stays reliable even without TOCs; we just need to keep tuning chunk size so retrieval latency stays reasonable.
- On the Alliade sample we only missed the image-only cover page; everything else came through once we stripped the TOC.
- Sherpa’s default `/parsing/` endpoint still truncates after the first pages. Passthrough now finishes but hands us raw layout blocks, so we can’t compare it fairly until we add a block→Markdown converter.
- Docling PRD gives the fastest wall-clock times right now; we note the per-env variance for future scheduling.

### 9. Next steps
1. Confirm whether Sherpa passthrough has an async flow; if not, keep experimenting with lighter params and smaller PDFs to avoid Gateway 504s.
2. Build or prototype the block→Markdown/chunk layer so Sherpa outputs something comparable to Docling.
3. Once both parsers are stable, run them over ~10 contracts with consistent `RUN_LABEL`s.
4. Keep the analyzer output current (coverage %, chunk counts, missing pages) and grow it into a small dashboard or notebook.
5. Draft comparison slides covering latency, coverage, and cost; use them to lock in the parser choice for Aria.
6. Feed the chosen parser into Promptflow so downstream teams can plug it into RAG without bespoke glue code.

### 10. Open todos
1. The 504 passthrough run is logged; no action beyond referencing it if CBAI needs repro details.
2. Sync with CBAI/Sherpa about timeout limits or async access.
3. Keep trying stripped-down Sherpa params (`renderFormat=text`, `applyOcr=no`, smaller PDFs) to see if we can make synchronous calls reliable.
4. Automate coverage reporting beyond the CSV (notebook or script).
5. Expand the corpus to 10 documents once Sherpa has a stable recipe.

### 11. Master plan (F1)

**Phase 1 – Baseline & metrics** (now)  
Run labeled Docling/Sherpa experiments, save payloads/metrics, and measure coverage.

**Phase 2 – Parser optimization**  
Docling: keep tuning chunking/OCR. Sherpa: unblock passthrough + build the block→Markdown converter.

**Phase 3 – Comparative eval**  
Once both parsers are usable, run the full 10-contract batch, capture timings + sample chunks, and set parser selection rules.

**Phase 4 – Integration & handoff**  
Wire the winner into Promptflow, share slides/docs, and move on to the multi-doc + contradiction tracks using the same logging discipline.

### References
- Aria background: 40-question legal risk RAG app.
- Docling API: `/start-parsing/` + `/result-parsing/{task_id}` via CBAI.
- LLM Sherpa API: `/parsing/` wrapper or `/passthrough/api/parseDocument` (<https://llmsherpa.readthedocs.io>).
