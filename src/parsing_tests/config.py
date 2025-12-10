from __future__ import annotations

import logging
import os
from typing import Optional

try:
    from openai import AzureOpenAI
except Exception:  # pragma: no cover - SDK might not be available in CI
    AzureOpenAI = None  # type: ignore[assignment]

from .utils.env import load_env

# Base logger for the project
logger = logging.getLogger("parsing_tests")
if not logger.handlers:
    logging.basicConfig(
        level=os.getenv("PARSING_TESTS_LOG_LEVEL", "INFO"),
        format="[%(asctime)s] - %(levelname)s : %(message)s",
    )


def _create_azure_openai_client() -> Optional["AzureOpenAI"]:
    endpoint = (os.getenv("AZURE_OPENAI_ENDPOINT") or "").strip()
    api_key = (os.getenv("AZURE_OPENAI_API_KEY") or "").strip()
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview").strip()

    if not endpoint or not api_key:
        logger.info(
            "Azure OpenAI endpoint or API key not configured; GPT parsing will be disabled."
        )
        return None
    if AzureOpenAI is None:
        logger.warning("Azure OpenAI SDK not installed; GPT parsing will be disabled.")
        return None

    try:
        return AzureOpenAI(
            azure_endpoint=endpoint.rstrip("/"),
            api_key=api_key,
            api_version=api_version,
        )
    except Exception as exc:  # pragma: no cover - runtime configuration failure
        logger.error("Failed to initialize Azure OpenAI client: %s", exc)
        return None


load_env()
azure_openai_client = _create_azure_openai_client()
azure_openai_gpt5_deployment = os.getenv("AZURE_OPENAI_GPT5_DEPLOYMENT")
