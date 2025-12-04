# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""Document parsing utilities for AI flashcard generation."""

from __future__ import annotations

import os
import re
from pathlib import Path

from anki.httpclient import HttpClient

# Token estimation constants
# Average characters per token for English text (rough approximation)
CHARS_PER_TOKEN = 4
# Maximum tokens for context window (leaving room for system prompt and response)
MAX_INPUT_TOKENS = 12000
MAX_CHARS = MAX_INPUT_TOKENS * CHARS_PER_TOKEN


class DocumentParseError(Exception):
    """Raised when document parsing fails."""

    pass


def parse_pdf(file_path: str) -> str:
    """Extract text content from a PDF file.

    Args:
        file_path: Path to the PDF file

    Returns:
        Extracted text content

    Raises:
        DocumentParseError: If the file cannot be parsed
    """
    try:
        import fitz  # type: ignore[import-untyped]  # PyMuPDF
    except ImportError as e:
        raise DocumentParseError(
            "PDF parsing requires PyMuPDF. Install with: pip install PyMuPDF"
        ) from e

    if not os.path.exists(file_path):
        raise DocumentParseError(f"File not found: {file_path}")

    try:
        doc = fitz.open(file_path)
        text_parts = []

        for page_num, page in enumerate(doc, start=1):
            page_text = page.get_text()
            if page_text.strip():
                text_parts.append(f"--- Page {page_num} ---\n{page_text}")

        doc.close()

        if not text_parts:
            raise DocumentParseError(
                "No text could be extracted from the PDF. "
                "The file may be scanned images without OCR."
            )

        return "\n\n".join(text_parts)

    except fitz.FileDataError as e:
        raise DocumentParseError(f"Invalid or corrupted PDF file: {e}") from e
    except Exception as e:
        raise DocumentParseError(f"Failed to parse PDF: {e}") from e


def parse_text_file(file_path: str) -> str:
    """Read content from a text file.

    Args:
        file_path: Path to the text file

    Returns:
        File content as string

    Raises:
        DocumentParseError: If the file cannot be read
    """
    if not os.path.exists(file_path):
        raise DocumentParseError(f"File not found: {file_path}")

    path = Path(file_path)
    if path.suffix.lower() not in (".txt", ".md", ".markdown", ".text"):
        raise DocumentParseError(
            f"Unsupported text file format: {path.suffix}. "
            "Supported formats: .txt, .md, .markdown"
        )

    try:
        # Try UTF-8 first, then fall back to other encodings
        encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
        content = None

        for encoding in encodings:
            try:
                content = path.read_text(encoding=encoding)
                break
            except UnicodeDecodeError:
                continue

        if content is None:
            raise DocumentParseError(
                "Could not decode file with any supported encoding"
            )

        if not content.strip():
            raise DocumentParseError("File is empty")

        return content

    except Exception as e:
        if isinstance(e, DocumentParseError):
            raise
        raise DocumentParseError(f"Failed to read file: {e}") from e


def parse_url(url: str) -> str:
    """Fetch and extract text content from a URL.

    Args:
        url: The URL to fetch

    Returns:
        Extracted text content

    Raises:
        DocumentParseError: If the URL cannot be fetched or parsed
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError as e:
        raise DocumentParseError(
            "URL parsing requires BeautifulSoup. Install with: pip install beautifulsoup4"
        ) from e

    # Basic URL validation
    if not url.startswith(("http://", "https://")):
        raise DocumentParseError("URL must start with http:// or https://")

    try:
        with HttpClient() as client:
            response = client.get(url)
            response.raise_for_status()
            html_content = client.stream_content(response)

        soup = BeautifulSoup(html_content, "html.parser")

        # Remove unwanted elements that typically contain non-content
        unwanted_selectors = [
            "script",
            "style",
            "nav",
            "footer",
            "header",
            "aside",
            "noscript",
            "iframe",
            "form",
            "[role='navigation']",
            "[role='banner']",
            "[role='contentinfo']",
            ".sidebar",
            ".menu",
            ".navigation",
            ".nav",
            ".footer",
            ".header",
            ".advertisement",
            ".ad",
            ".social-share",
            ".comments",
            "#sidebar",
            "#menu",
            "#navigation",
            "#nav",
            "#footer",
            "#header",
        ]
        for selector in unwanted_selectors:
            for element in soup.select(selector):
                element.decompose()

        # Try to find main content area with multiple strategies
        main_content = None

        # Strategy 1: Look for semantic HTML5 elements
        main_content = soup.find("main") or soup.find("article")

        # Strategy 2: Look for common content container IDs
        if not main_content:
            for content_id in [
                "content",
                "main-content",
                "main",
                "article",
                "post",
                "entry",
                "page-content",
                "body-content",
            ]:
                main_content = soup.find(id=content_id)
                if main_content:
                    break

        # Strategy 3: Look for common content container classes
        if not main_content:
            for content_class in [
                "content",
                "main-content",
                "article-content",
                "post-content",
                "entry-content",
                "page-content",
                "article-body",
                "post-body",
            ]:
                main_content = soup.find(class_=content_class)
                if main_content:
                    break

        # Strategy 4: Look for role="main"
        if not main_content:
            main_content = soup.find(attrs={"role": "main"})

        # Strategy 5: Find the largest text container
        if not main_content:
            # Fall back to finding the div with the most paragraph content
            from bs4 import Tag

            divs_with_paragraphs: list[tuple[Tag, int]] = []
            for div in soup.find_all("div"):
                if isinstance(div, Tag):
                    paragraphs = div.find_all("p", recursive=True)
                    if paragraphs:
                        total_text = sum(
                            len(p.get_text(strip=True))
                            for p in paragraphs
                            if isinstance(p, Tag)
                        )
                        divs_with_paragraphs.append((div, total_text))

            if divs_with_paragraphs:
                # Sort by text length and take the one with most content
                divs_with_paragraphs.sort(key=lambda x: x[1], reverse=True)
                main_content = divs_with_paragraphs[0][0]

        # Strategy 6: Fall back to body
        if not main_content:
            main_content = soup.find("body")

        if main_content:
            text = main_content.get_text(separator="\n", strip=True)
        else:
            text = soup.get_text(separator="\n", strip=True)

        # Clean up excessive whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" {2,}", " ", text)

        if not text.strip():
            raise DocumentParseError("No text content could be extracted from the URL")

        return text

    except DocumentParseError:
        raise
    except Exception as e:
        raise DocumentParseError(f"Failed to fetch URL: {e}") from e


def parse_pasted_text(text: str) -> str:
    """Process pasted text content.

    Args:
        text: The pasted text

    Returns:
        Cleaned text content

    Raises:
        DocumentParseError: If the text is empty
    """
    if not text or not text.strip():
        raise DocumentParseError("Pasted text is empty")

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Clean up excessive whitespace while preserving paragraph breaks
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)

    return text.strip()


def estimate_tokens(text: str) -> int:
    """Estimate the number of tokens in the text.

    This is a rough estimate based on character count.
    For accurate counting, use tiktoken with the specific model's tokenizer.

    Args:
        text: The text to estimate tokens for

    Returns:
        Estimated token count
    """
    # Try to use tiktoken for accurate counting
    try:
        import tiktoken

        # Use cl100k_base encoding (used by gpt-4, gpt-3.5-turbo)
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except ImportError:
        # Fall back to character-based estimation
        return len(text) // CHARS_PER_TOKEN


def chunk_text(text: str, max_tokens: int = MAX_INPUT_TOKENS) -> list[str]:
    """Split text into chunks that fit within token limits.

    Args:
        text: The text to chunk
        max_tokens: Maximum tokens per chunk

    Returns:
        List of text chunks
    """
    # Estimate total tokens
    total_tokens = estimate_tokens(text)

    if total_tokens <= max_tokens:
        return [text]

    # Split by paragraphs first
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk: list[str] = []
    current_tokens = 0

    for para in paragraphs:
        para_tokens = estimate_tokens(para)

        # If a single paragraph is too large, split by sentences
        if para_tokens > max_tokens:
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_tokens = 0

            # Split long paragraph by sentences
            sentences = re.split(r"(?<=[.!?])\s+", para)
            for sentence in sentences:
                sent_tokens = estimate_tokens(sentence)
                if current_tokens + sent_tokens > max_tokens:
                    if current_chunk:
                        chunks.append(" ".join(current_chunk))
                    current_chunk = [sentence]
                    current_tokens = sent_tokens
                else:
                    current_chunk.append(sentence)
                    current_tokens += sent_tokens
        elif current_tokens + para_tokens > max_tokens:
            # Start a new chunk
            chunks.append("\n\n".join(current_chunk))
            current_chunk = [para]
            current_tokens = para_tokens
        else:
            current_chunk.append(para)
            current_tokens += para_tokens

    # Don't forget the last chunk
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    return chunks


def get_source_name(source: str, source_type: str) -> str:
    """Extract a human-readable source name.

    Args:
        source: The source path, URL, or identifier
        source_type: Type of source ("file", "url", "paste")

    Returns:
        A clean source name for display and tagging
    """
    if source_type == "file":
        return Path(source).name
    elif source_type == "url":
        # Extract domain and path
        from urllib.parse import urlparse

        parsed = urlparse(source)
        path = parsed.path.strip("/")
        if path:
            return f"{parsed.netloc}/{path.split('/')[-1]}"
        return parsed.netloc
    else:
        # For pasted text, use a generic name
        return "pasted_text"
