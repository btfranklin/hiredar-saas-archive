"""
PDF text extraction utilities.

This module contains functions for extracting text content from resume PDFs.
"""

import logging
from typing import Optional

import pdfplumber

# Setup logging
logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_path: str) -> Optional[str]:
    """
    Extract text content from a PDF file.

    Args:
        file_path: Path to the PDF file

    Returns:
        The extracted text content or None if extraction fails
    """
    try:
        text_content = []

        with pdfplumber.open(file_path) as pdf:
            # Extract text from each page
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_content.append(text)

        # Join all the text with newlines
        return "\n".join(text_content)

    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        return None
