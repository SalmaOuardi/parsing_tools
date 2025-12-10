import os
import time

from ..gpt.page_parser import parse_pdf_document
from ..utils.env import load_env
from ..utils.result_exporter import append_metrics, save_json_payload


def _str_to_bool(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def main() -> None:
    load_env()
    pdf_path = os.getenv("GPT_PARSER_PDF_PATH", "data/sample.pdf")
    experiment_label = os.getenv("RUN_LABEL")
    run_notes = os.getenv("RUN_NOTES", "")
    image_description = _str_to_bool(os.getenv("GPT_PARSER_IMAGE_DESCRIPTION"))
    extra_instruction = os.getenv("GPT_PARSER_EXTRA_INSTRUCTION")

    start = time.perf_counter()
    payload = parse_pdf_document(
        pdf_path,
        image_description=image_description,
        additional_instruction=extra_instruction,
    )
    duration = time.perf_counter() - start

    result_path = save_json_payload("gpt5", pdf_path, payload, experiment=experiment_label)
    metrics_path = append_metrics(
        "gpt5",
        pdf_path,
        payload,
        duration_seconds=duration,
        parser_env="azure",
        experiment=experiment_label,
        extra={"notes": run_notes},
    )

    print(f"Saved GPT-5 payload to {result_path}")
    print(f"Appended GPT-5 metrics to {metrics_path}")


if __name__ == "__main__":
    main()
