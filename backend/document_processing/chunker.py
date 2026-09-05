"""Deterministic text chunking for extracted documents.

Chunks are stored in the `document_chunks` table (DocumentChunk model) and
prepared for later RAG / semantic retrieval phases. Chunking keeps paragraphs
intact where possible and overlaps long runs so no information is lost at
boundaries. No AI is involved — this is pure text processing.
"""
import re

MAX_CHUNK_CHARS = 6000
OVERLAP_CHARS = 300


def chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS,
               overlap: int = OVERLAP_CHARS) -> list[str]:
    """Split extracted text into a list of chunk strings.

    Paragraph boundaries (blank lines) are preserved. A single paragraph larger
    than max_chars is hard-split into windows with `overlap` trailing
    characters carried into the next window.
    """
    text = (text or "").replace("\r\n", "\n").strip()
    if not text:
        return []

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        if len(para) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(_hard_split(para, max_chars, overlap))
            continue
        if current and len(current) + len(para) + 2 > max_chars:
            chunks.append(current)
            tail = current[-overlap:] if overlap and len(current) > overlap else ""
            current = tail
        current = f"{current}\n\n{para}" if current else para

    if current:
        chunks.append(current)
    return chunks


def _hard_split(text: str, max_chars: int, overlap: int) -> list[str]:
    """Split one oversized paragraph into windows with overlap."""
    windows: list[str] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + max_chars, length)
        if end < length:
            # try to break at a sentence boundary near the window end
            look = text.rfind(". ", start + max_chars // 2, end)
            if look != -1:
                end = look + 1
        windows.append(text[start:end].strip())
        if end >= length:
            break
        start = max(end - overlap, start + 1)
    return [w for w in windows if w]


def count_tokens(chunk: str) -> int:
    """Approximate token count (4 chars ≈ 1 token) for bookkeeping."""
    return max(1, len(chunk) // 4)
