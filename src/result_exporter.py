import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RESULTS_DIR = Path("data/results")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def save_json_payload(parser_name: str, pdf_path: str, payload: dict[str, Any]) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    pdf_stem = Path(pdf_path).stem.replace(" ", "_")
    filename = f"{parser_name.lower()}_{pdf_stem}_{timestamp}.json"
    target = RESULTS_DIR / filename
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return target


def append_metrics(
    parser_name: str,
    pdf_path: str,
    payload: dict[str, Any],
    duration_seconds: float,
    extra: dict[str, Any] | None = None,
) -> Path:
    csv_path = RESULTS_DIR / "metrics.csv"
    fieldnames = [
        "timestamp",
        "parser",
        "pdf_path",
        "status",
        "duration_seconds",
        "chunk_count",
        "execution_time",
        "notes",
    ]
    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "parser": parser_name,
        "pdf_path": pdf_path,
        "status": payload.get("status") or payload.get("state") or "",
        "duration_seconds": f"{duration_seconds:.2f}",
        "chunk_count": _infer_chunk_count(payload),
        "execution_time": _infer_execution_time(payload),
        "notes": "",
    }
    if extra:
        row.update({k: v for k, v in extra.items() if k in fieldnames})

    write_header = not csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow(row)
    return csv_path


def _infer_chunk_count(payload: dict[str, Any]) -> int:
    result = payload.get("result")
    if isinstance(result, dict) and isinstance(result.get("content"), list):
        return len(result["content"])
    if isinstance(payload.get("chunks"), list):
        return len(payload["chunks"])
    return 0


def _infer_execution_time(payload: dict[str, Any]) -> str:
    result = payload.get("result")
    exec_time = None
    if isinstance(result, dict):
        exec_time = result.get("execution_time")
    if exec_time is None and isinstance(payload.get("meta"), dict):
        exec_time = payload["meta"].get("execution_time")
    return str(exec_time) if exec_time is not None else ""
