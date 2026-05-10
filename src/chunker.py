from __future__ import annotations

import re


def normalize_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 150) -> list[str]:
    text = normalize_text(text)
    if not text:
        return []
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap")

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = end - overlap
    return chunks


def pages_to_chunks(
    pages: list[dict],
    chunk_size: int = 1000,
    overlap: int = 150,
) -> list[dict]:
    chunks: list[dict] = []
    for page in pages:
        page_chunks = chunk_text(page.get("text", ""), chunk_size=chunk_size, overlap=overlap)
        for local_index, text in enumerate(page_chunks, start=1):
            chunk_id = f"{page['source_file']}::p{page['page']}::c{local_index}"
            chunks.append(
                {
                    "text": text,
                    "source_file": page["source_file"],
                    "page": page["page"],
                    "chunk_id": chunk_id,
                }
            )
    return chunks
