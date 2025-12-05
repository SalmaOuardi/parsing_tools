## Weekly Update – Week of 1 Dec 2025

**Feature:** Aria TOC-less parsing  
**Owner:** Salma Ouardi  

### 1. What We’re Solving
- Aria needs to read long “appel d’offres” PDFs even when there’s no table of contents and still answer our 40 risk questions with proper citations.
- To get there, I’m benchmarking Docling vs LLM Sherpa (both exposed through CBAI) so we can pick one parser that’s fast, complete, and easy to drop into the RAG flow.

### 2. Progress This Week
- **Tooling & logging:** wrapped both parsers in small CLIs that share the same `.env`. Every run now saves the full JSON payload under `data/results/` and adds a row to `data/results/metrics.csv` (timestamp, parser, env, duration, chunk count, notes). Also synced all context into `docs/parser_playbook.md` and started a checkbox TODO list.
- **Docling experiments:** ran the 97‑page `reseau ASF.pdf` on TST/PPD/PRD with the default 7.5k-token chunks just to observe latency/coverage. Then dropped `max_token_per_chunk` to 1 500 on PRD—result: ~240 chunks, ~400 seconds, clean Markdown that still respects the document structure.
- **Sherpa experiments:** tried the default `/parsing/` endpoint (PRD) with chunk size 800. It only produced 73 chunks and most of the document content vanished (lots of empty bullet chunks). Switched to `/passthrough/api/parseDocument` with `renderFormat=all`, `strategy=chunks`, `applyOcr=yes`, `useNewIndentParser=yes`. Two runs with extended timeouts (180s and 480s) both failed—first run timed out on our side, second returned a 504 Gateway Timeout. Logged the failures so they show up alongside the successful Docling run.
### 3. Key Takeaways
- Docling looks stable on the sample we have, but we still need to validate it against contracts that truly lack a TOC before calling it done.
- Sherpa via `/parsing/` isn’t usable yet—it drops too much content. Passthrough is promising but needs either async support or lighter parameters to avoid 504s.
- Having every run logged (payload + metrics) makes comparisons easy, even when a run fails.

### 4. Plan for Next 
1. **Talk to CBAI/Sherpa** about async support or higher timeouts for passthrough so we can keep OCR/render-all turned on without hitting a 504.
2. **Parameter sweeps:** experiment with different Sherpa flags (disable OCR, `renderFormat=text`, smaller chunk sizes, smaller PDFs). One change per run, tracked via `RUN_LABEL`.
3. **Coverage metrics script:** build a quick notebook/script that reads the saved payloads and reports % pages covered, non-empty chunk rate, average tokens per chunk.
4. **Prepare the 10-contract batch:** once Sherpa is stable, run Docling vs Sherpa on the full set of sample contracts (use naming scheme `docling-1500-contractNN`, `sherpa-tuned-contractNN`).
### 5. Help Needed
- A confirmation from CBAI/Sherpa on whether passthrough can run asynchronously (like Docling’s start/result pattern) or if there’s a higher timeout cap we can request.
- Extra contract samples (without a TOC)

We’re still testing both parsers—the current PDF actually has a TOC, so the next step is to run the same experiments on contracts that truly lack one before we declare either parser “ready.”
