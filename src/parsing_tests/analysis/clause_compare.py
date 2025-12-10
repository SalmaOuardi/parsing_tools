from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple


def load_chunks(path: Path) -> List[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("chunks", [])


def index_clauses(chunks: List[dict]) -> Dict[str, List[dict]]:
    by_clause: Dict[str, List[dict]] = defaultdict(list)
    for chunk in chunks:
        clause_id = chunk.get("clause_id") or "UNKNOWN"
        by_clause[clause_id].append(chunk)
    return by_clause


def compare_clauses(docling_chunks: List[dict], sherpa_chunks: List[dict]) -> Dict[str, Tuple[int, int]]:
    docling_index = index_clauses(docling_chunks)
    sherpa_index = index_clauses(sherpa_chunks)
    clause_ids = sorted(set(docling_index.keys()) | set(sherpa_index.keys()))
    comparison: Dict[str, Tuple[int, int]] = {}
    for clause_id in clause_ids:
        comparison[clause_id] = (
            len(docling_index.get(clause_id, [])),
            len(sherpa_index.get(clause_id, [])),
        )
    return comparison


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare clause-aware chunk outputs produced by clause_chunker.py"
    )
    parser.add_argument("--docling", required=True, type=Path, help="Path to Docling clause chunk JSON.")
    parser.add_argument("--sherpa", required=True, type=Path, help="Path to Sherpa clause chunk JSON.")
    parser.add_argument("--limit", type=int, default=20, help="Limit rows shown in the console.")
    args = parser.parse_args()

    docling_chunks = load_chunks(args.docling)
    sherpa_chunks = load_chunks(args.sherpa)
    comparison = compare_clauses(docling_chunks, sherpa_chunks)

    sorted_items = sorted(comparison.items(), key=lambda item: item[0])
    print(f"Total clauses (Docling): {len(index_clauses(docling_chunks))}")
    print(f"Total clauses (Sherpa): {len(index_clauses(sherpa_chunks))}")
    print("Clause ID | Docling chunks | Sherpa chunks")
    print("------------------------------------------")
    for clause_id, (d_count, s_count) in sorted_items[: args.limit]:
        print(f"{clause_id:<15} {d_count:<15} {s_count:<15}")


if __name__ == "__main__":
    main()
