## Clause-Aware Chunking Comparison

### Sherpa passthrough
- Source: `data/results/llmsherpa_alliade-habitat_no_toc_20251207_193933_sherpa-passthrough-alliade-no-toc.json`
- Block structure keeps clause headings and body paragraphs separate with `block_idx`, `tag`, `level`, and `page_idx`.
- Clause `12.2.2` maps to blocks `[330, 331]`, so each layout unit already knows its clause context before chunking.

### Docling
- Source: `data/results/docling_alliade-habitat_no_toc_20251207_193842_docling-alliade-no-toc.json`
- Outputs Markdown-ready chunks with `chunk_id`, `chunk_page`, and `chunk_content` only.
- Clause `12.2.2` sits inside chunk `63`, meaning we must parse heading text ourselves and maintain clause state if the clause gets split.

### Decision
- We will proceed with Sherpa because its passthrough payload exposes clause boundaries directly, which makes clause-level metadata trivial to propagate through downstream chunking.
- Blocking issue: the passthrough API times out on larger PDFs (504 Gateway). We still need to solve that (lighter params, async support, or smaller batches) before Sherpa can replace Docling in the pipeline.
