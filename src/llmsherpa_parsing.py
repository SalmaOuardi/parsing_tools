import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from env_utils import get_env_value, load_env

'''
LLM Sherpa Parsing CLI
'''

log_format = "[%(asctime)s] - %(levelname)s : %(message)s"
logging.basicConfig(level=logging.INFO, format=log_format)

load_env()


@dataclass(frozen=True)
class SherpaSettings:
    preserve_layout: bool = True
    chunk_token_size: int = 800
    overlap_tokens: int = 100

    def to_payload(self) -> dict[str, Any]:
        return {
            "preserve_layout": self.preserve_layout,
            "chunk_token_size": self.chunk_token_size,
            "overlap_tokens": self.overlap_tokens,
        }


class LLMSherpaClient:
    def __init__(self, base_url: str, api_key: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._session = requests.Session()

    def parse_document(self, pdf_path: str | Path, settings: SherpaSettings) -> dict[str, Any]:
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        url = f"{self.base_url}/document"
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        with pdf_path.open("rb") as pdf_file:
            files = {"file": (pdf_path.name, pdf_file, "application/pdf")}
            data = {"settings": json.dumps(settings.to_payload())}
            response = self._session.post(
                url,
                headers=headers,
                data=data,
                files=files,
                timeout=int(os.getenv("LLMSHERPA_TIMEOUT", "120")),
            )

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            body = exc.response.text if exc.response is not None else "<no body>"
            status = exc.response.status_code if exc.response else "unknown"
            logging.error("LLM Sherpa request failed (%s): %s", status, body)
            raise
        return response.json()


def main() -> None:
    base_url = os.getenv("LLMSHERPA_URL")
    if not base_url:
        raise RuntimeError("Missing LLMSHERPA_URL in environment or .env file")

    api_key = get_env_value(os.getenv("LLMSHERPA_API_KEY_VAR", "LLMSHERPA_API_KEY"))
    pdf_path = os.getenv("LLMSHERPA_PDF_PATH", r"data/sample.pdf")

    client = LLMSherpaClient(base_url, api_key)
    settings = SherpaSettings(
        preserve_layout=_str_to_bool(os.getenv("LLMSHERPA_PRESERVE_LAYOUT", "true")),
        chunk_token_size=_optional_int(os.getenv("LLMSHERPA_CHUNK_SIZE"), default=800),
        overlap_tokens=_optional_int(os.getenv("LLMSHERPA_CHUNK_OVERLAP"), default=100),
    )

    logging.info(
        "LLM Sherpa URL=%s | PDF=%s | Settings=%s",
        base_url,
        pdf_path,
        settings,
    )
    result = client.parse_document(pdf_path, settings)
    logging.info("LLM Sherpa response: %s", json.dumps(result, indent=2))


def _optional_int(raw_value: str | None, default: int) -> int:
    if not raw_value:
        return default
    try:
        return int(raw_value)
    except ValueError:
        logging.warning("Expected integer but received '%s', falling back to %s", raw_value, default)
        return default


def _str_to_bool(value: str) -> bool:
    value = (value or "").strip().lower()
    return value in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    main()
