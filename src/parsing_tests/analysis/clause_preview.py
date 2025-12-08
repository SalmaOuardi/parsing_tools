from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

HEADING_REGEX = re.compile(r"^\s*(\d+(?:\.\d+)+)\s+(.*)")


@dataclass
class Unit:
    unit_id: int
    page: int
    text: str


@dataclass
class Clause:
    clause_id: str
    title: str
    units: List[Unit] = field(default_factory=list)

    def add_unit(self, unit: Unit) -> None:
        self.units.append(unit)

    @property
    def pages(self) -> Sequence[int]:
        return sorted({unit.page for unit in self.units})

    @property
    def unit_ids(self) -> Sequence[int]:
        return [unit.unit_id for unit in self.units]


def iter_docling_units(path: Path) -> Iterable[Unit]:
    payload = json.loads(path.read_text(encoding="utf-8"))["result"]["content"]
    for entry in payload:
        text = entry.get("chunk_content", "").strip()
        if not text:
            continue
        yield Unit(
            unit_id=entry.get("chunk_id", -1),
            page=entry.get("chunk_page", -1),
            text=text,
        )


def iter_sherpa_units(path: Path) -> Iterable[Unit]:
    blocks = json.loads(path.read_text(encoding="utf-8"))["return_dict"]["result"]["blocks"]
    for block in blocks:
        sentences = block.get("sentences") or []
        text = " ".join(sentence.strip() for sentence in sentences).strip()
        if not text:
            continue
        yield Unit(
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


def build_clauses(units: Iterable[Unit]) -> List[Clause]:
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview clause groupings for parser outputs.")
    parser.add_argument("--parser", choices=("docling", "sherpa"), required=True)
    parser.add_argument("--file", type=Path, required=True)
    parser.add_argument("--clause-id", help="Filter down to a specific clause number (e.g., 12.2.2).")
    parser.add_argument("--limit", type=int, default=5, help="Max clauses to display when no filter is provided.")
    args = parser.parse_args()

    if args.parser == "docling":
        units = list(iter_docling_units(args.file))
    else:
        units = list(iter_sherpa_units(args.file))

    clauses = build_clauses(units)
    if args.clause_id:
        clauses = [clause for clause in clauses if clause.clause_id == args.clause_id]
        if not clauses:
            raise SystemExit(f"No clause '{args.clause_id}' found in {args.file}.")
    else:
        clauses = clauses[: args.limit]

    for clause in clauses:
        unit_type = "chunk" if args.parser == "docling" else "block"
        print(f"Clause {clause.clause_id}: {clause.title}")
        print(f"  Pages: {clause.pages}")
        print(f"  {unit_type}_ids: {clause.unit_ids}")
        for unit in clause.units:
            preview = unit.text.replace("\n", " ")[:160]
            print(f"    - {unit_type} {unit.unit_id} (page {unit.page}): {preview}")
        print()


if __name__ == "__main__":
    main()
