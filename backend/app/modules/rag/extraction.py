"""Text extraction and normalisation for uploaded study material.

Accepted: PDF, DOCX, Markdown, plain text. The file type is checked from its content, not
just its name, and limits stop oversized or malformed uploads from tying up the API.
PDF pages are marked as `[[page N]]` lines so passages can cite the page they came from.
"""

import io
import re
import unicodedata
import zipfile
from dataclasses import dataclass

MAX_PAGES = 400
MAX_CHARS = 2_000_000

KINDS = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".txt": "text/plain",
}

PAGE_MARK = re.compile(r"^\[\[page (\d+)\]\]$", re.M)


class ExtractionError(Exception):
    pass


@dataclass
class Extracted:
    text: str
    mime_type: str
    page_count: int | None


def _ext(name: str) -> str:
    m = re.search(r"\.[A-Za-z0-9]+$", name or "")
    return m.group(0).lower() if m else ""


def extract(file_name: str, data: bytes) -> Extracted:
    ext = _ext(file_name)
    if ext not in KINDS:
        raise ExtractionError("Upload a PDF, Word (.docx), Markdown (.md) or text (.txt) file.")
    if not data:
        raise ExtractionError("The file is empty.")
    if ext == ".pdf":
        if not data.startswith(b"%PDF"):
            raise ExtractionError("That file isn't a valid PDF.")
        text, pages = _pdf(data)
    elif ext == ".docx":
        if not data.startswith(b"PK"):
            raise ExtractionError("That file isn't a valid Word document.")
        text, pages = _docx(data), None
    else:
        if b"\x00" in data[:4096]:
            raise ExtractionError("That doesn't look like a text file.")
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError as e:
            raise ExtractionError("Text files must be UTF-8 encoded.") from e
        pages = None
    text = normalise(text)
    if len(text) > MAX_CHARS:
        raise ExtractionError("The document is too long. Split it into smaller files.")
    if len(PAGE_MARK.sub("", text).strip()) < 40:
        raise ExtractionError(
            "No readable text was found. Scanned PDFs need OCR before they can be used."
        )
    return Extracted(text, KINDS[ext], pages)


def _pdf(data: bytes) -> tuple[str, int]:
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise ExtractionError("Password-protected PDFs can't be processed.")
        n = len(reader.pages)
        if n > MAX_PAGES:
            raise ExtractionError(f"PDFs are limited to {MAX_PAGES} pages.")
        parts = []
        for i, page in enumerate(reader.pages, start=1):
            parts.append(f"[[page {i}]]\n{page.extract_text() or ''}")
        return "\n\n".join(parts), n
    except ExtractionError:
        raise
    except (PdfReadError, ValueError, KeyError, TypeError) as e:
        raise ExtractionError("The PDF couldn't be read.") from e


def _docx(data: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            if "word/document.xml" not in z.namelist():
                raise ExtractionError("That file isn't a valid Word document.")
            if sum(i.file_size for i in z.infolist()) > 200 * 1024 * 1024:
                raise ExtractionError("The Word document is too large once unpacked.")
        import docx

        doc = docx.Document(io.BytesIO(data))
    except ExtractionError:
        raise
    except (zipfile.BadZipFile, KeyError, ValueError) as e:
        raise ExtractionError("The Word document couldn't be read.") from e
    lines = []
    for p in doc.paragraphs:
        t = p.text.strip()
        if not t:
            continue
        style = (p.style.name if p.style is not None else "") or ""
        m = re.match(r"Heading (\d)", style)
        lines.append(f"{'#' * min(int(m.group(1)), 4)} {t}" if m else t)
    for table in doc.tables:
        for row in table.rows:
            lines.append(" | ".join(c.text.strip() for c in row.cells))
    return "\n\n".join(lines)


_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def normalise(text: str) -> str:
    """Unicode NFKC, no control characters, rejoined hyphenated line breaks, tidy spacing.
    Maths inside $…$ is left alone (NFKC keeps TeX intact)."""
    text = unicodedata.normalize("NFKC", text).replace("\r\n", "\n").replace("\r", "\n")
    text = _CONTROL.sub("", text)
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)  # "accele-\nration" → "acceleration"
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
