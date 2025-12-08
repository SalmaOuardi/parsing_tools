"""
Comparison helper for Docling vs LLM Sherpa outputs.

Reads a JSON config listing parser runs, loads the saved JSON payloads,
and computes coverage metrics (pages touched, coverage %, unit counts).

Usage:
    uv run python -m parsing_tests.analysis.coverage_cli \
        --config data/results/alliade_runs.json \
        --out-csv data/results/alliade_comparison_metrics.csv
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Iterable, List, Sequence

import pymupdf  # type: ignore


@dataclass(frozen=True)
class RunConfig:
    label: str
    parser: str
    pdf_path: Path
    result_path: Path
    variant: str | None = None


@dataclass
class RunMetrics:
    label: str
    parser: str
    variant: str | None
    pdf_path: str
    pdf_pages: int
    covered_pages: int
    coverage_ratio: float
    unit_name: str
    unit_count: int
    avg_tokens: float | None
    missing_pages: Sequence[int]
    result_path: str

    def to_row(self) -> List[str]:
        """Convert to CSV-friendly row."""
        return [
            self.label,
            self.parser,
            self.variant or "",
            self.pdf_path,
            str(self.pdf_pages),
            str(self.covered_pages),
            f"{self.coverage_ratio:.2%}",
            self.unit_name,
            str(self.unit_count),
            f"{self.avg_tokens:.1f}" if self.avg_tokens is not None else "",
            ";".join(str(p) for p in self.missing_pages) or "none",
            self.result_path,
        ]


def load_config(path: Path) -> List[RunConfig]:
    data = json.loads(path.read_text(encoding="utf-8"))
    runs: List[RunConfig] = []
    for item in data:
        runs.append(
            RunConfig(
                label=item["label"],
                parser=item["parser"].lower(),
                pdf_path=Path(item["pdf_path"]),
                result_path=Path(item["result_path"]),
                variant=item.get("variant"),
            )
        )
    return runs


def analyze_docling(run: RunConfig, pdf_pages: int) -> RunMetrics:
    payload = json.loads(run.result_path.read_text(encoding="utf-8"))
    content = payload["result"]["content"]
    unit_name = "chunks"
    unit_count = len(content)
    page_numbers = [entry.get("chunk_page") for entry in content if isinstance(entry, dict)]
    pages = sorted({int(p) for p in page_numbers if isinstance(p, int)})
    tokens = [entry.get("chunk_token", 0) or 0 for entry in content if isinstance(entry, dict)]
    missing = sorted(set(range(1, pdf_pages + 1)) - set(pages))
    return RunMetrics(
        label=run.label,
        parser=run.parser,
        variant=run.variant,
        pdf_path=str(run.pdf_path),
        pdf_pages=pdf_pages,
        covered_pages=len(pages),
        coverage_ratio=len(pages) / pdf_pages if pdf_pages else 0.0,
        unit_name=unit_name,
        unit_count=unit_count,
        avg_tokens=mean(tokens) if tokens else None,
        missing_pages=missing,
        result_path=str(run.result_path),
    )


def analyze_llmsherpa(run: RunConfig, pdf_pages: int) -> RunMetrics:
    payload = json.loads(run.result_path.read_text(encoding="utf-8"))
    sherpa_result = payload["return_dict"]["result"]
    blocks = sherpa_result.get("blocks", [])
    unit_name = "blocks"
    page_numbers = [
        int(block["page_idx"]) + 1
        for block in blocks
        if isinstance(block, dict) and isinstance(block.get("page_idx"), int)
    ]
    pages = sorted(set(page_numbers))
    missing = sorted(set(range(1, pdf_pages + 1)) - set(pages))
    return RunMetrics(
        label=run.label,
        parser=run.parser,
        variant=run.variant,
        pdf_path=str(run.pdf_path),
        pdf_pages=pdf_pages,
        covered_pages=len(pages),
        coverage_ratio=len(pages) / pdf_pages if pdf_pages else 0.0,
        unit_name=unit_name,
        unit_count=len(blocks),
        avg_tokens=None,
        missing_pages=missing,
        result_path=str(run.result_path),
    )


def analyze_run(run: RunConfig) -> RunMetrics:
    pdf_pages = len(pymupdf.open(run.pdf_path))
    if run.parser == "docling":
        return analyze_docling(run, pdf_pages)
    if run.parser in {"llmsherpa", "sherpa"}:
        return analyze_llmsherpa(run, pdf_pages)
    raise ValueError(f"Unsupported parser '{run.parser}'")


def write_csv(metrics: Iterable[RunMetrics], output_path: Path) -> None:
    rows = list(metrics)
    header = [
        "label",
        "parser",
        "variant",
        "pdf_path",
        "pdf_pages",
        "covered_pages",
        "coverage_ratio",
        "unit_name",
        "unit_count",
        "avg_tokens",
        "missing_pages",
        "result_path",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(header)
        for metric in rows:
            writer.writerow(metric.to_row())


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compute coverage metrics for Docling and LLM Sherpa runs."
    )
    parser.add_argument("--config", required=True, type=Path, help="JSON file listing runs.")
    parser.add_argument(
        "--out-csv",
        type=Path,
        default=Path("data/results/comparison_metrics.csv"),
        help="Where to store the aggregated metrics CSV.",
    )
    args = parser.parse_args()

    runs = load_config(args.config)
    metrics = [analyze_run(run) for run in runs]
    write_csv(metrics, args.out_csv)

    print(f"Wrote {len(metrics)} rows to {args.out_csv}")
    for metric in metrics:
        missing_desc = "none" if not metric.missing_pages else ", ".join(
            f"p{page}" for page in metric.missing_pages
        )
        print(
            f"{metric.label:<35} parser={metric.parser:<10} coverage={metric.coverage_ratio:.1%} "
            f"({metric.covered_pages}/{metric.pdf_pages} pages) "
            f"units={metric.unit_count} {metric.unit_name} | missing pages: {missing_desc}"
        )


if __name__ == "__main__":
    main()
