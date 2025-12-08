"""
PDF page-based parsing utilities.

This module contains helpers to split a PDF into single page images.
It exposes functions to parse a single page image
and to orchestrate a full-document chunked parsing pipeline that
reassembles results into a single `ParsedDocument` model.

Notes:
    - Functions depend on global clients and credentials in `config`.
    - When SDKs or credentials are missing, functions log errors and may
      raise RuntimeError.
    - Exported functions:
        - parse_pdf_page()
        - parse_pdf_page_by_page()
"""

from pathlib import Path
import base64
from io import BytesIO
from typing import List
import uuid

from PIL import Image
import pymupdf

from ...config import logger, azure_openai_client
from ...utils.models import ParsedDocument, ParsedDocumentBase


def parse_pdf_page(
    image_b64: str,
    image_description: bool = False,
    additional_instruction: str = None,
) -> str:
    """
    Sends a single base64-encoded page image to the GPT-4 Vision model
    and asks it to convert the content to Markdown.

    Args:
        image_b64 (str): A base64 encoded string of the page image.
        image_description (bool, optional): If True, request brief image
            descriptions instead of removing images. Defaults to False.
        additional_instruction (str, optional): Additional user instruction
            to append to the base instruction set. Defaults to None.

    Returns:
        The Markdown content of the page as a string.
    """
    # Prepare instructions for the LLM
    if image_description:
        image_instruction = (
            "Remove the figure/image and replace it with a concise, descriptive "
            "placeholder in the format "
            "`[Image: A brief, accurate description of the image content]`."
        )
    else:
        image_instruction = (
            "Remove all figures/images from the document and do not mention them "
            "or replace them with any description."
        )
    system_instruction = (
        "You are an expert PDF-to-Markdown conversion engine. "
        "Your sole task is to accurately extract the main content of a PDF page "
        "and reformat it into clean, well-structured markdown.\n\n"
        "## Core Directives\n\n"
        "* **Content Scope:** Process **only the main body** of the document.\n"
        "* **Content Integrity:** Preserve the original text, wording, and language "
        "**exactly** as it appears. You must not add, fabricate, summarize or omit any "
        "information from the main content.\n"
        "* **Structural Fidelity:** Replicate the original document's structure, "
        "including the hierarchy of headings, paragraphs, lists, etc.\n\n"
        "* **Paragraphs:** Write each paragraph on a single line. Separate paragraphs "
        "with a blank line (two line breaks).\n"
        "---\n\n"
        "## Formatting Rules\n\n"
        "* **Headings:** Use markdown heading levels (`#`, `##`, `###`) to match the "
        "original document's hierarchy.\n"
        "* **Text Styles:** Preserve **bold** using `**text**` and *italics* using "
        "`*text*`.\n"
        "* **Lists:** Convert all bulleted and numbered lists into proper markdown "
        "(`-`, `*`, `1.`, `2.`)\n"
        "* **Tables:** Recreate tables using markdown table syntax.\n"
        "* **Formulas:** Transcribe all mathematical equations/formulas into LaTeX. "
        "Use `$formula$` for inline equations and `$$formula$$` for block equations.\n"
        f"* **Figures & Images:** {image_instruction}\n"
        "* **Code Blocks:** Format any source code using markdown's triple backticks "
        "(```), specifying the language if possible (e.g., ` ```python `).\n\n"
        "---\n\n"
        "## Content to Exclude\n\n"
        "You **must** ignore and completely discard all of the following elements. "
        "Do not mention them in the output.\n\n"
        "* **Front Matter:** Title page, author details, affiliations, abstract, "
        "keywords, table of contents, list of figures, list of tables, preface, "
        "foreword, acknowledgments.\n"
        "* **Back Matter:** Bibliography, references, appendices, and index.\n"
        "* **Page Metadata:** All page headers, page footers, and page numbers."
        "**DO NOT USE YOUR PERSONAL KNOWLEDGE**\n"
        "**DO NOT MAKE UP ANY INFORMATION**\n"
    )
    if additional_instruction:
        system_instruction += "\n" + additional_instruction
    user_instruction = (
        "Parse the following PDF page. Make sure to preserve the original text, "
        "wording, and language EXACTLY as it appears. You must not add, fabricate, "
        "summarize, or omit any information from the main content."
    )

    # Send the page to the LLM for parsing.
    if azure_openai_client is None:
        logger.error("Azure OpenAI client not initialized; cannot parse page image.")
        raise RuntimeError("Azure OpenAI client not initialized.")
    response = azure_openai_client.chat.completions.create(
        model="gpt-5",
        messages=[
            {"role": "system", "content": system_instruction},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                    },
                    user_instruction,
                ],
            },
        ],
    )

    # The SDK returns choices; access message content
    return response.choices[0].message.content


def parse_pdf_page_by_page(
    pdf_path: str,
    page_delimiter: str,
    image_description: bool = False,
    additional_instruction: str = None,
) -> ParsedDocument:
    """
    Parses a PDF into Markdown by converting each page to an image and
    using a vision LLM for OCR and formatting.

    Args:
        pdf_path (str): The file path to the PDF document.
        page_delimiter (str): The delimiter to use between pages in the Markdown
            output.
        image_description (bool, optional): If True, request brief image
            descriptions instead of removing images. Defaults to False.
        additional_instruction (str, optional): Additional user instruction
            to append to the base instruction set. Defaults to None.

    Returns:
        ParsedDocument: A complete `ParsedDocument` model including concatenated content from all
            pages.
    """
    # Open the PDF and get the number of pages.
    full_pdf = pymupdf.open(pdf_path)
    nb_pages = len(full_pdf)

    # Process each page individually.
    chunk_docs: List[ParsedDocument] = []
    for page_num in range(nb_pages):
        # Load specific page
        logger.debug(f"Processing page {page_num + 1} of {nb_pages}...")
        page_pdf = full_pdf.load_page(page_num)

        # Convert the page to a high-resolution image for better OCR results.
        pix = page_pdf.get_pixmap(dpi=150)
        image = Image.open(BytesIO(pix.tobytes()))
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        image_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        # Send the page image to the LLM for parsing.
        try:
            logger.debug(f"Sending page {page_num + 1} to vision LLM.")
            page_content = parse_pdf_page(
                image_b64, image_description, additional_instruction
            )
        except Exception as e:
            logger.error(f"Error parsing page {page_num + 1}: {e}")
            page_content = f"Error parsing page {page_num + 1}: {str(e)}"

        # Add the page delimiter before the page content.
        page_content = f"<PAGE_{page_num + 1}>\n{page_content}"

        # Create a ChunkDoc for the page with its content and metadata.
        chunk_doc = ParsedDocumentBase(
            title=f"Page {page_num + 1}",
            content=page_content,
        )

        # Append the parsed chunk to the list of chunk documents.
        chunk_docs.append(chunk_doc)
    logger.info("Finished parsing all pages with vision LLM.")

    # Concatenate all page contents into a single Document.
    return ParsedDocument(
        id=str(uuid.uuid4()),
        name=Path(pdf_path).name,
        path=str(pdf_path),
        title=Path(pdf_path).stem,
        content=page_delimiter.join([chunk_doc.content for chunk_doc in chunk_docs]),
    )
