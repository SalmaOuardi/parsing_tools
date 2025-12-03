import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl

import requests

from env_utils import get_env_value, load_env
from result_exporter import append_metrics, save_json_payload

'''
LLM Sherpa Parsing CLI
'''

log_format = "[%(asctime)s] - %(levelname)s : %(message)s"
logging.basicConfig(level=logging.INFO, format=log_format)

load_env()


LLMSHERPA_ENVIRONMENTS = {
    "TST": {
        "base_url": "https://api-tst.vinci-construction.net/cbai/v1/llm_sherpa",
        "api_key_var": "CBAI_API_KEY_TST",
    },
    "PPD": {
        "base_url": "https://api-ppd.vinci-construction.net/cbai/v1/llm_sherpa",
        "api_key_var": "CBAI_API_KEY_PPD",
    },
    "PRD": {
        "base_url": "https://api.vinci-construction.net/cbai/v1/llm_sherpa",
        "api_key_var": "CBAI_API_KEY_PRD",
    },
}


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
    def __init__(
        self,
        base_url: str,
        api_key: str | None,
        endpoint: str,
        extra_params: dict[str, str],
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.endpoint = endpoint.strip("/")
        self.extra_params = extra_params
        self._session = requests.Session()

    def parse_document(self, pdf_path: str | Path, settings: SherpaSettings) -> dict[str, Any]:
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        url = f"{self.base_url}/{self.endpoint}"
        headers = {"Accept": "application/json"}
        params = dict(self.extra_params)
        if self.api_key:
            params["API_KEY"] = self.api_key

        with pdf_path.open("rb") as pdf_file:
            files = {"file": (pdf_path.name, pdf_file, "application/pdf")}
            data = {"settings": json.dumps(settings.to_payload())}
            response = self._session.post(
                url,
                headers=headers,
                params=params,
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
    base_url, api_key, env_name = resolve_llmsherpa_credentials()
    endpoint = os.getenv("LLMSHERPA_ENDPOINT", "parsing/")
    extra_params = parse_extra_params(os.getenv("LLMSHERPA_QUERY"))
    pdf_path = os.getenv("LLMSHERPA_PDF_PATH", r"data/sample.pdf")
    experiment_label = os.getenv("RUN_LABEL")
    run_notes = os.getenv("RUN_NOTES", "")

    client = LLMSherpaClient(base_url, api_key, endpoint=endpoint, extra_params=extra_params)
    settings = SherpaSettings(
        preserve_layout=_str_to_bool(os.getenv("LLMSHERPA_PRESERVE_LAYOUT", "true")),
        chunk_token_size=_optional_int(os.getenv("LLMSHERPA_CHUNK_SIZE"), default=800),
        overlap_tokens=_optional_int(os.getenv("LLMSHERPA_CHUNK_OVERLAP"), default=100),
    )

    logging.info(
        "LLM Sherpa ENV=%s | URL=%s/%s | PDF=%s | Settings=%s | params=%s | Run=%s",
        env_name,
        base_url,
        endpoint,
        pdf_path,
        settings,
        extra_params,
        experiment_label or "<none>",
    )
    start = time.perf_counter()
    result = client.parse_document(pdf_path, settings)
    duration = time.perf_counter() - start
    logging.info("LLM Sherpa response: %s", json.dumps(result, indent=2))

    result_path = save_json_payload("llmsherpa", pdf_path, result, experiment=experiment_label)
    metrics_path = append_metrics(
        "llmsherpa",
        pdf_path,
        result,
        duration,
        parser_env=env_name,
        experiment=experiment_label,
        extra={
            "notes": run_notes or f"{env_name} layout={settings.preserve_layout}",
        },
    )
    logging.info("Saved LLM Sherpa payload to %s", result_path)
    logging.info("Appended LLM Sherpa metrics to %s", metrics_path)


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


def resolve_llmsherpa_credentials() -> tuple[str, str | None, str]:
    env_name = (os.getenv("LLMSHERPA_ENV") or "TST").upper()
    env_config = LLMSHERPA_ENVIRONMENTS.get(env_name)
    if not env_config:
        logging.warning("Unknown LLMSHERPA_ENV '%s', defaulting to TST", env_name)
        env_name = "TST"
        env_config = LLMSHERPA_ENVIRONMENTS[env_name]

    base_url = os.getenv("LLMSHERPA_URL", env_config["base_url"])
    api_key_var = os.getenv("LLMSHERPA_API_KEY_VAR", env_config["api_key_var"])
    api_key = get_env_value(api_key_var)
    return base_url.rstrip("/"), api_key, env_name


def parse_extra_params(raw_value: str | None) -> dict[str, str]:
    if not raw_value:
        return {}
    return {key: value for key, value in parse_qsl(raw_value, keep_blank_values=True)}


if __name__ == "__main__":
    main()
