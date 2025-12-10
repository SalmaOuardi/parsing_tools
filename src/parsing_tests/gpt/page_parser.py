from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path
from typing import List

import fitz  # type: ignore[attr-defined]
from PIL import Image

from ..config import (
    azure_openai_client,
    azure_openai_gpt5_deployment,
    logger,
)


def _build_system_instruction(image_description: bool, extra: str | None = None) -> str:
    if image_description:
        image_instruction = (
            "Replace each image with a concise placeholder such as "
            "`[Image: short, accurate description]`."
        )
    else:
        image_instruction = "Remove all figures/images without mentioning them."

    system_instruction = (
        "You are an expert PDF-to-Markdown engine. "
        "Extract the main body text exactly as written and render it as clean Markdown.\n\n"
        "Rules:\n"
        "- Preserve headings, structure, and numbering.\n"
        "- Keep paragraphs verbatim (no paraphrasing or summarising).\n"
        "- Use Markdown lists/tables when the source uses lists/tables.\n"
        "- Preserve **bold** and *italics* markers where they exist.\n"
        f"- {image_instruction}\n"
        "- Ignore headers, footers, and page numbers.\n"
        "- Ignore TOCs, front matter, and appendices unless explicitly instructed."
    )
    if extra:
        system_instruction += "\n" + extra.strip()
    return system_instruction


def parse_pdf_page(
    image_b64: str,
    image_description: bool = False,
    additional_instruction: str | None = None,
) -> str:
    """
    Sends a base64 encoded PNG page to the GPT-5 deployment and returns Markdown text.
    """
    if azure_openai_client is None or not azure_openai_gpt5_deployment:
        raise RuntimeError("Azure OpenAI client or deployment name not configured.")

    system_instruction = _build_system_instruction(
        image_description=image_description,
        extra=additional_instruction,
    )
    user_message = (
        "Parse the attached PDF page and return the Markdown content exactly as written."
    )

    response = azure_openai_client.chat.completions.create(
        model=azure_openai_gpt5_deployment,
        messages=[
            {"role": "system", "content": system_instruction},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                    },
                    {
                        "type": "text",
                        "text": user_message,
                    },
                ],
            },
        ],
    )
    choice = response.choices[0].message.content
    return choice or ""


def parse_pdf_document(
    pdf_path: str | Path,
    *,
    dpi: int = 150,
    image_description: bool = False,
    additional_instruction: str | None = None,
) -> dict:
    """
    Converts a PDF into Markdown chunks by sending each page through GPT-5 vision.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    logger.info("Parsing %s with GPT-5 (dpi=%s)", pdf_path, dpi)
    document = fitz.open(str(pdf_path))
    chunks: List[dict] = []

    for page_index in range(document.page_count):
        page_number = page_index + 1
        page = document.load_page(page_index)
        pix = page.get_pixmap(dpi=dpi)
        image = Image.open(BytesIO(pix.tobytes()))
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        image_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        try:
            content = parse_pdf_page(
                image_b64=image_b64,
                image_description=image_description,
                additional_instruction=additional_instruction,
            )
        except Exception as exc:  # pragma: no cover - remote failures
            logger.error("Failed to parse page %s: %s", page_number, exc)
            content = f"<!-- Error parsing page {page_number}: {exc} -->"

        chunks.append(
            {
                "page": page_number,
                "content": content.strip(),
            }
        )

    payload = {
        "parser": "gpt-5",
        "pdf_path": str(pdf_path),
        "meta": {"page_count": document.page_count},
        "chunks": chunks,
        "status": "completed",
    }
    return payload
