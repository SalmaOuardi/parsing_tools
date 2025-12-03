import json
import logging
import os
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import requests

from env_utils import get_env_value, load_env
from result_exporter import append_metrics, save_json_payload

'''
Docling Parsing CLI
'''

# Configuration du logging
log_format = "[%(asctime)s] - %(levelname)s : %(message)s"
logging.basicConfig(level=logging.INFO, format=log_format)


load_env()


DOC_ENVIRONMENTS = {
    "TST": {
        "url": "https://api-tst.vinci-construction.net/cbai/v1/docling",
        "api_key_var": "CBAI_API_KEY_TST",
    },
    "PPD": {
        "url": "https://api-ppd.vinci-construction.net/cbai/v1/docling",
        "api_key_var": "CBAI_API_KEY_PPD",
    },
    "PRD": {
        "url": "https://api.vinci-construction.net/cbai/v1/docling",
        "api_key_var": "CBAI_API_KEY_PRD",
    },
}


class ExportType(str, Enum):
    MARKDOWN = "markdown"
    JSON = "json"


class ChunkingType(str, Enum):
    HYBRID = "hybrid"
    NONE = "none"


@dataclass(frozen=True)
class PdfSettings:
    export_type: ExportType = ExportType.MARKDOWN
    chunking_type: ChunkingType = ChunkingType.HYBRID
    picture_description_model: str | None = None
    picture_description_prompt: str | None = None
    max_token_per_chunk: int | None = None

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "export_type": self.export_type.value,
            "chunking_type": self.chunking_type.value,
        }
        if self.picture_description_model is not None:
            payload["picture_description_model"] = self.picture_description_model
        if self.picture_description_prompt is not None:
            payload["picture_description_prompt"] = self.picture_description_prompt
        if self.max_token_per_chunk is not None:
            payload["max_token_per_chunk"] = self.max_token_per_chunk
        return payload


class DoclingClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._session = requests.Session()

    def start_parsing(self, pdf_path: str | Path, pdf_settings: PdfSettings) -> dict[str, Any]:
        """Send the PDF to the Docling REST API."""
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        url = f"{self.base_url}/start-parsing/"
        params = {"API_KEY": self.api_key}
        payload = pdf_settings.to_payload()
        with pdf_path.open("rb") as pdf_file:
            files = {"file": (pdf_path.name, pdf_file, "application/pdf")}
            response = self._session.post(
                url,
                params=params,
                headers={"Accept": "application/json"},
                data={"settings": json.dumps(payload)},
                files=files,
                timeout=120,
            )
        return self._handle_response(response, "Docling start failed")

    def get_result(self, task_id: str) -> dict[str, Any]:
        """Retrieve the parsing result for the given task."""
        url = f"{self.base_url}/result-parsing/{task_id}"
        params = {"API_KEY": self.api_key}
        response = self._session.get(
            url,
            params=params,
            headers={"Accept": "application/json"},
            timeout=60,
        )
        return self._handle_response(response, "Docling result failed")

    def wait_for_completion(
        self,
        pdf_path: str | Path,
        pdf_settings: PdfSettings,
        poll_interval: float,
        max_attempts: int,
    ) -> dict[str, Any]:
        """Start a parsing job and wait for the final result."""
        start_response = self.start_parsing(pdf_path, pdf_settings)
        logging.info("Docling start response: %s", json.dumps(start_response, indent=2))

        task_id = start_response.get("task_id")
        if not task_id:
            raise RuntimeError("Docling did not return a task_id")

        if start_response.get("result"):
            logging.info("Docling completed synchronously for %s", task_id)
            return start_response

        return poll_for_result(
            self,
            task_id,
            poll_interval=poll_interval,
            max_attempts=max_attempts,
        )

    @staticmethod
    def _handle_response(response: requests.Response, context: str) -> dict[str, Any]:
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            body = exc.response.text if exc.response is not None else "<no body>"
            status = exc.response.status_code if exc.response else "unknown"
            logging.error("%s (%s): %s", context, status, body)
            raise
        return response.json()


def poll_for_result(
    client: DoclingClient,
    task_id: str,
    poll_interval: float = 5.0,
    max_attempts: int = 20,
) -> dict[str, Any]:
    """Poll the result endpoint until it leaves Pending or attempts exhausted."""
    for attempt in range(1, max_attempts + 1):
        result = client.get_result(task_id)
        status = (result.get("status") or "").lower()
        has_payload = result.get("result") not in (None, "")
        logging.info(
            "Result poll %s/%s: status=%s payload=%s",
            attempt,
            max_attempts,
            status or "<unknown>",
            "yes" if has_payload else "no",
        )
        if has_payload or (status and status not in {"pending", "processing"}):
            return result
        time.sleep(poll_interval)
    raise TimeoutError(f"Docling task {task_id} did not finish after {max_attempts} attempts")


def _choice_from_env(env_key: str, enum_cls: type[Enum], default: Enum) -> Enum:
    raw_value = os.getenv(env_key)
    if not raw_value:
        return default
    normalized = raw_value.strip().lower()
    for member in enum_cls:
        if member.value == normalized:
            return member
    logging.warning(
        "Unknown value '%s' for %s, falling back to %s",
        raw_value,
        env_key,
        default.value,
    )
    return default


def build_pdf_settings_from_env() -> PdfSettings:
    return PdfSettings(
        export_type=_choice_from_env("DOCLING_EXPORT_TYPE", ExportType, ExportType.MARKDOWN),
        chunking_type=_choice_from_env("DOCLING_CHUNKING_TYPE", ChunkingType, ChunkingType.HYBRID),
        picture_description_model=os.getenv("DOCLING_PICTURE_MODEL", ""),
        picture_description_prompt=os.getenv(
            "DOCLING_PICTURE_PROMPT",
            "Describe the image in French in three sentences. Be consise and accurate.",
        ),
        max_token_per_chunk=_optional_int(os.getenv("DOCLING_MAX_TOKEN_PER_CHUNK"), default=7500),
    )


def _optional_int(raw_value: str | None, default: int | None = None) -> int | None:
    if raw_value is None or raw_value == "":
        return default
    try:
        return int(raw_value)
    except ValueError:
        logging.warning("Expected integer for value '%s', falling back to %s", raw_value, default)
        return default


def resolve_docling_credentials() -> tuple[str, str, str]:
    env_name = (os.getenv("DOCLING_ENV") or "TST").upper()
    env_config = DOC_ENVIRONMENTS.get(env_name)
    if not env_config:
        logging.warning("Unknown DOCLING_ENV '%s', falling back to TST", env_name)
        env_name = "TST"
        env_config = DOC_ENVIRONMENTS[env_name]

    base_url = os.getenv("DOCLING_URL", env_config["url"])
    api_key_var = os.getenv("DOCLING_API_KEY_VAR", env_config["api_key_var"])
    api_key = get_env_value(api_key_var)
    if not api_key:
        raise RuntimeError(f"Missing {api_key_var} in environment or .env file")
    return base_url.rstrip("/"), api_key, env_name


def main() -> None:
    docling_url, docling_api_key, env_name = resolve_docling_credentials()

    pdf_path = os.getenv("DOCLING_PDF_PATH", r"data\reseau ASF.pdf")
    poll_interval = float(os.getenv("DOCLING_POLL_INTERVAL", "5"))
    max_attempts = int(os.getenv("DOCLING_POLL_ATTEMPTS", "40"))

    client = DoclingClient(docling_url, docling_api_key)
    pdf_settings = build_pdf_settings_from_env()
    logging.info(
        "Docling ENV=%s | URL=%s | PDF=%s | Settings=%s",
        env_name,
        docling_url,
        pdf_path,
        pdf_settings,
    )

    start = time.perf_counter()
    final_result = client.wait_for_completion(
        pdf_path,
        pdf_settings,
        poll_interval=poll_interval,
        max_attempts=max_attempts,
    )
    duration = time.perf_counter() - start
    logging.info("Docling final result: %s", json.dumps(final_result, indent=2))

    result_path = save_json_payload("docling", pdf_path, final_result)
    metrics_path = append_metrics(
        "docling",
        pdf_path,
        final_result,
        duration,
        extra={"notes": env_name},
    )
    logging.info("Saved Docling payload to %s", result_path)
    logging.info("Appended Docling metrics to %s", metrics_path)


if __name__ == "__main__":
    main()
