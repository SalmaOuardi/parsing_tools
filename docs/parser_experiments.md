## Aria TOC-less Parsing – Experiment Log

### 7. Run history (F1)

| Date (UTC) | RUN_LABEL | Parser | Env | Key settings | Duration (s) | Exec time (s) | Units | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2025-12-03 | `docling-7500-default` | Docling | TST/PPD/PRD | `max_chunk=7500` | 627 / 538 / 408 / 468 | 293–456 | 235 chunks | Coverage OK, chunks too fat. |
| 2025-12-03 | `docling-1500-vs-sherpa` | Docling | PRD | `max_chunk=1500` | 397 | 387 | 240 chunks | Balanced baseline. |
| 2025-12-03 | `docling-1500-vs-sherpa` | Sherpa (`parsing/`) | PRD | `chunk_size=800` | 9 | n/a | 73 chunks | Drops content after first pages. |
| 2025-12-03 | `baseline-docling-1500-vs-sherpa-passthrough` | Sherpa passthrough | PRD | `renderFormat=all&applyOcr=yes` + 480 s timeout | 244 (timeout) | n/a | 0 | CBAI 504 after ~4.5 min. |
| 2025-12-07 | `docling-alliade-toc` | Docling | PRD | `data/alliade-habitat.pdf`, `max_chunk=1500` | 282–343 | 70 / 64 | 136 chunks | Full coverage with TOC (cover image skipped). |
| 2025-12-07 | `docling-alliade-no-toc` | Docling | PRD | `data/alliade-habitat_no_toc.pdf` | 362 | 63 | 132 chunks | Clean Article 1–27 flow without TOC. |
| 2025-12-07 | `sherpa-passthrough-alliade-toc` | Sherpa passthrough | PRD | `renderFormat=all&strategy=chunks&applyOcr=yes` | 14 | n/a | 750 blocks | Full layout blocks; no Markdown yet. |
| 2025-12-07 | `sherpa-passthrough-alliade-no-toc` | Sherpa passthrough | PRD | same as above | 8 | n/a | 629 blocks | Same story without the TOC. |

We keep adding rows after each run (references live under `data/results/`).

### Coverage snapshot

Command:

```powershell
uv run python -m parsing_tests.analysis.coverage_cli `
  --config data/results/alliade_runs.json `
  --out-csv data/results/alliade_comparison_metrics.csv
```

| RUN_LABEL | Variant | Pages covered | Coverage % | Units | Avg tokens | Missing pages | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `docling-alliade-toc` | with TOC | 38 / 39 | 97.4% | 136 chunks | 279 | p4 (cover image) | Markdown-ready. |
| `docling-alliade-no-toc` | no TOC | 35 / 35 | 100% | 132 chunks | 254 | none | Matches body text exactly. |
| `sherpa-passthrough-alliade-toc` | with TOC | 39 / 39 | 100% | 750 blocks | n/a | none | Needs block→chunk pass. |
| `sherpa-passthrough-alliade-no-toc` | no TOC | 35 / 35 | 100% | 629 blocks | n/a | none | Same as above without TOC. |

CSV: `data/results/alliade_comparison_metrics.csv`.

### Parser call for the GPT benchmark
- **Docling** goes head-to-head with GPT. It already gives us Markdown chunks with manageable token counts, covered the full body on both PDFs, and only skipped the image-only cover page.
- **Sherpa passthrough** stays on deck until we build a block→Markdown/chunk reconstructor. Right now it would be an apples-to-oranges comparison because the output is still raw layout metadata.

### Sherpa passthrough reliability (vinci-ccg-180)
- Baseline params (`renderFormat=all&strategy=chunks&applyOcr=yes&useNewIndentParser=yes`) finished in ~32 s and produced `data/results/sherpa_passthrough_vinci-ccg-180.json` (1 817 blocks, 141 / 180 pages). Missing ranges are mostly annex/image pages (121‑135, 142, 144, 146, 148, 151‑170, 175‑178).
- Switching to `applyOcr=no` kept the same coverage (1 817 blocks, 141 / 180 pages), so OCR isn’t what skips the annexes. File: `data/results/sherpa_passthrough_vinci-ccg-180_applyOcrNo.json`.
- Forcing `renderFormat=text` returned only `{num_pages, page_dim}` (file: `data/results/sherpa_passthrough_vinci-ccg-180_renderText.json`), so that mode isn’t usable for structured output.
- Conclusion: we stay on the `renderFormat=all` payload and keep experimenting with other knobs (strategy, smaller batches) to recover the final pages before wiring clause metadata.
- Follow-up tests:
  - `strategy=sections` produced the exact same payload as the baseline (`data/results/sherpa_passthrough_vinci-ccg-180_sections.json`), so that flag doesn’t change coverage either.
  - Adding `pageStart` / `pageEnd` query params had no effect—the API still returned all 180 pages, meaning page slicing isn’t exposed via passthrough today (`data/results/sherpa_passthrough_vinci-ccg-180_pages01-100.json`, `..._pages120-180.json`).
  - Bottom line: `renderFormat=all&strategy=chunks&applyOcr=yes&useNewIndentParser=yes` stays our working config while we design the clause-aware block→chunk layer. We’ll revisit once CBAI/Sherpa offer async or better page control.
