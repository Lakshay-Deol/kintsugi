"""Page-aware PDF chunker.

Produces chunks with metadata: brand, model, manual_id, page, section, type.
Figure/table chunks are optional (cut-order item 2).
Ingestion runs locally only — never on Render.
"""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

CHUNK_TYPE_TEXT = "text"
CHUNK_TYPE_TABLE = "table"
CHUNK_TYPE_FIGURE = "figure"


def _page_hash(manual_id: str, page: int, chunk_idx: int) -> str:
    raw = f"{manual_id}:{page}:{chunk_idx}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def chunk_pdf(
    pdf_path: Path,
    manual_id: str,
    brand: str,
    model: str,
    *,
    max_chars: int = 1200,
    include_tables: bool = True,
) -> list[dict[str, Any]]:
    """
    Parse a PDF into page-aware chunks with metadata.
    Returns list of chunk dicts ready for Atlas insertion (sans embedding).
    """
    import pdfplumber

    chunks: list[dict[str, Any]] = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                # Extract text
                text = page.extract_text() or ""
                text = text.strip()

                if text:
                    # Split long pages into overlapping windows
                    for idx, segment in enumerate(_split_text(text, max_chars)):
                        chunk: dict[str, Any] = {
                            "_id": _page_hash(manual_id, page_num, idx),
                            "manual_id": manual_id,
                            "brand": brand,
                            "model": model,
                            "page": page_num,
                            "section": _detect_section(text),
                            "type": CHUNK_TYPE_TEXT,
                            "text": segment,
                            "embedding": [],  # filled by ingest pipeline
                        }
                        chunks.append(chunk)

                # Extract tables (cut-order item 2 — enabled by default)
                if include_tables:
                    tables = page.extract_tables() or []
                    for t_idx, table in enumerate(tables):
                        table_text = _table_to_text(table)
                        if table_text:
                            chunk = {
                                "_id": _page_hash(manual_id, page_num, 1000 + t_idx),
                                "manual_id": manual_id,
                                "brand": brand,
                                "model": model,
                                "page": page_num,
                                "section": _detect_section(text),
                                "type": CHUNK_TYPE_TABLE,
                                "text": table_text,
                                "embedding": [],
                            }
                            chunks.append(chunk)

    except Exception as exc:
        log.error("Failed to chunk PDF %s: %s", pdf_path, exc)
        raise

    log.info("Chunked %s: %d chunks across %d-page PDF", pdf_path.name, len(chunks), page_num)
    return chunks


def _split_text(text: str, max_chars: int) -> list[str]:
    """Split text into overlapping windows."""
    if len(text) <= max_chars:
        return [text]
    overlap = max_chars // 4
    segments = []
    start = 0
    while start < len(text):
        end = start + max_chars
        segments.append(text[start:end])
        start += max_chars - overlap
    return segments


def _detect_section(text: str) -> str:
    """Naive section header detection from first line."""
    lines = text.split("\n")
    for line in lines[:5]:
        stripped = line.strip()
        if stripped and len(stripped) < 80 and stripped.isupper():
            return stripped
    return ""


def _table_to_text(table: list[list[str | None]]) -> str:
    """Flatten a pdfplumber table to pipe-delimited text."""
    rows = []
    for row in table:
        cells = [str(c).strip() if c else "" for c in row]
        rows.append(" | ".join(cells))
    return "\n".join(rows)
