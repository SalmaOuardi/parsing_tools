from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

HEADING_REGEX = re.compile(r"^\s*(\d+(?:\.\d+)+)\s+(.*)")


@dataclass
class SourceUnit:
    unit_id: int
    page: int
    text: str


@dataclass
class Clause:
    clause_id: str
    title: str
    units: List[SourceUnit] = field(default_factory=list)

    def add_unit(self, unit: SourceUnit) -> None:
        self.units.append(unit)

    @property
    def pages(self) -> Sequence[int]:
        return sorted({unit.page for unit in self.units if unit.page >= 0})


def iter_docling_units(path: Path) -> Iterable[SourceUnit]:
    content = json.loads(path.read_text(encoding="utf-8"))["result"]["content"]
    for chunk in content:
        text = chunk.get("chunk_content", "").strip()
        if not text:
            continue
        yield SourceUnit(
            unit_id=chunk.get("chunk_id", -1),
            page=chunk.get("chunk_page", -1),
            text=text,
        )


def iter_sherpa_units(path: Path) -> Iterable[SourceUnit]:
    blocks = json.loads(path.read_text(encoding="utf-8"))["return_dict"]["result"]["blocks"]
    for block in blocks:
        sentences = block.get("sentences") or []
        text = " ".join(sentence.strip() for sentence in sentences).strip()
        if not text:
            continue
        yield SourceUnit(
            unit_id=block.get("block_idx", -1),
            page=1 + block.get("page_idx", -1),
            text=text,
        )


def extract_heading(text: str) -> Optional[tuple[str, str]]:
    first_line = text.splitlines()[0].strip()
    match = HEADING_REGEX.match(first_line)
    if not match:
        return None
    return match.group(1), first_line


def build_clauses(units: Iterable[SourceUnit]) -> List[Clause]:
    clauses: List[Clause] = []
    current: Optional[Clause] = None
    for unit in units:
        heading = extract_heading(unit.text)
        if heading:
            clause_id, title = heading
            current = Clause(clause_id=clause_id, title=title)
            clauses.append(current)

        if current:
            current.add_unit(unit)
    return clauses


def chunk_clause(clause: Clause, chunk_char_limit: int) -> List[dict]:
    chunks: List[dict] = []
    buffer: List[str] = []
    unit_ids: List[int] = []
    pages: List[int] = []
    chunk_index = 0

    def flush() -> None:
        nonlocal buffer, unit_ids, pages, chunk_index
        if not buffer:
            return
        chunk_index += 1
        text = "\n".join(buffer).strip()
        chunks.append(
            {
                "clause_id": clause.clause_id,
                "clause_title": clause.title,
                "chunk_index": chunk_index,
                "text": text,
                "unit_ids": unit_ids[:],
                "pages": sorted({page for page in pages if page >= 0}),
            }
        )
        buffer = []
        unit_ids = []
        pages = []

    for unit in clause.units:
        unit_text = unit.text.strip()
        if not unit_text:
            continue
        # Start a new chunk if the buffer would exceed the limit.
        prospective_length = sum(len(part) for part in buffer) + len(buffer) + len(unit_text)
        if buffer and prospective_length > chunk_char_limit:
            flush()
        buffer.append(unit_text)
        unit_ids.append(unit.unit_id)
        pages.append(unit.page)
        # Handle extremely large single units by flushing immediately.
        if len(unit_text) >= chunk_char_limit:
            flush()

    flush()
    return chunks


def chunk_document(units: Iterable[SourceUnit], chunk_char_limit: int) -> List[dict]:
    clauses = build_clauses(units)
    chunks: List[dict] = []
    for clause in clauses:
        clause_chunks = chunk_clause(clause, chunk_char_limit)
        chunks.extend(clause_chunks)
    return chunks


def main() -> None:
    parser = argparse.ArgumentParser(description="Clause-aware chunking for parser payloads.")
    parser.add_argument("--parser", choices=("docling", "sherpa"), required=True, help="Source parser type.")
    parser.add_argument("--file", type=Path, required=True, help="Path to the JSON payload to process.")
    parser.add_argument("--chunk-chars", type=int, default=1200, help="Maximum character count per chunk.")
    parser.add_argument("--out", type=Path, help="Optional path to save the chunked JSON.")
    args = parser.parse_args()

    if args.parser == "docling":
        units = list(iter_docling_units(args.file))
    else:
        units = list(iter_sherpa_units(args.file))

    chunks = chunk_document(units, chunk_char_limit=max(200, args.chunk_chars))
    output = {"source": str(args.file), "parser": args.parser, "chunk_char_limit": args.chunk_chars, "chunks": chunks}

    if args.out:
        args.out.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Saved {len(chunks)} clause-aware chunks to {args.out}")
    else:
        print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
