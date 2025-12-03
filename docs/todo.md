## TODO – Aria Parsing Experiments

- [ ] **LLM Sherpa passthrough – async confirmation**  
  - [ ] Contact CBAI/Sherpa team to confirm if `/passthrough/api/parseDocument` supports an asynchronous start/result flow (similar to Docling).  
  - [ ] If yes, design the start/poll integration.

- [ ] **Sherpa parameter sweeps (sync)**  
  - [ ] Remove/alter heavy params (`applyOcr`, `renderFormat=all`, etc.) and re-run with new `RUN_LABEL`s.  
  - [ ] Test splitting large PDFs to understand size limits.

- [ ] **Automated coverage metrics**  
  - [ ] Implement a script/notebook that reports % pages covered, non-empty chunk rate, average tokens per chunk from `data/results/*.json`.  
  - [ ] Export summaries next to `metrics.csv`.

- [ ] **Extended corpus runs**  
  - [ ] Once Sherpa config stabilizes, run both parsers on ~10 contracts (CCAP/AE/RC + CCAG).  
  - [ ] Use consistent experiment naming (`docling-1500-contractNN`, `sherpa-tuned-contractNN`).

- [ ] **Comparison slides**  
  - [ ] Build deck highlighting latency, cost, parsing fidelity, and recommended parser.  
  - [ ] Document failed attempts (timeouts, coverage issues) for transparency.

- [ ] **Promptflow integration planning**  
  - [ ] Outline integration steps (PDF ingestion, chunk metadata, multi-doc readiness).  
  - [ ] Schedule implementation once parser selection is finalized.
