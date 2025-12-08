"""
Utility script to remove Table of Contents pages from a PDF.

Example:
    uv run python -m parsing_tests.cli.remove_toc \
        --input data/reseau ASF.pdf \
        --output data/reseau ASF_no_toc.pdf \
        --pages 2-5
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, List

import pymupdf


def _parse_pages_arg(pages_arg: str, total_pages: int) -> List[int]:
    """Parse a string like ``1,3,5-7`` into zero-based page indexes."""
    if not pages_arg:
        raise ValueError("No pages provided. Use --pages to list pages to delete.")

    pages: set[int] = set()
    for part in pages_arg.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_str, end_str = part.split("-", maxsplit=1)
            start = int(start_str)
            end = int(end_str)
            if start > end:
                raise ValueError(f"Invalid range '{part}': start is greater than end.")
            range_pages = range(start, end + 1)
            pages.update(range_pages)
        else:
            pages.add(int(part))

    invalid = [p for p in pages if p < 1 or p > total_pages]
    if invalid:
        raise ValueError(
            f"Pages out of bounds: {invalid}. PDF has {total_pages} pages (1-indexed)."
        )

    # Convert to zero-based indexes sorted descending (needed for deletion)
    return sorted((p - 1 for p in pages), reverse=True)


def remove_pages(input_pdf: Path, output_pdf: Path, pages_to_remove: Iterable[int]) -> None:
    """Delete the supplied zero-based page indexes from the input PDF."""
    doc = pymupdf.open(input_pdf)
    try:
        for page_index in pages_to_remove:
            doc.delete_page(page_index)
        output_pdf.parent.mkdir(parents=True, exist_ok=True)
        doc.save(output_pdf)
    finally:
        doc.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Create a TOC-less copy of a PDF by deleting specific pages. "
            "Pages use 1-based numbering like the document."
        )
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to the original PDF that still contains a TOC.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help=(
            "Path for the TOC-less PDF. Defaults to appending '_no_toc' before "
            "the extension in the input filename."
        ),
    )
    parser.add_argument(
        "--pages",
        required=True,
        help=(
            "Comma-separated list of 1-based page numbers or ranges to delete "
            "(e.g. '2,3-5,7')."
        ),
    )
    args = parser.parse_args()

    if not args.input.exists():
        raise FileNotFoundError(f"Input PDF not found: {args.input}")

    doc = pymupdf.open(args.input)
    total_pages = len(doc)
    doc.close()

    pages_to_remove = _parse_pages_arg(args.pages, total_pages)

    output_path = (
        args.output
        if args.output
        else args.input.with_name(f"{args.input.stem}_no_toc{args.input.suffix}")
    )

    remove_pages(args.input, output_path, pages_to_remove)

    print(
        f"Removed pages {args.pages} from '{args.input}' "
        f"and saved TOC-less copy to '{output_path}'."
    )


if __name__ == "__main__":
    main()
