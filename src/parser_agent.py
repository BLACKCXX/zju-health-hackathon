from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .chunker import chunk_text
from .config import get_settings, list_pdf_files
from .document_parser import parse_document, infer_book_title
from .textbook_store import TextbookStore


# Book name mapping for the 7 standard textbooks
BOOK_NAME_MAP = {
    "01_局部解剖学.pdf": "局部解剖学",
    "02_组织学与胚胎学.pdf": "组织学与胚胎学",
    "03_生理学.pdf": "生理学",
    "04_医学微生物学.pdf": "医学微生物学",
    "05_病理学.pdf": "病理学",
    "06_传染病学.pdf": "传染病学",
    "07_病理生理学.pdf": "病理生理学",
}


def infer_book_name(source_file: str) -> str:
    """Infer book title from source filename."""
    return BOOK_NAME_MAP.get(source_file, infer_book_title(source_file))


def infer_chapter(text: str) -> str:
    """Infer chapter name from text."""
    for line in text.split("\n")[:12]:
        clean = line.strip()
        if not clean:
            continue
        if re.search(r"第[一二三四五六七八九十百0-9]+章", clean):
            return clean[:80]
        if re.search(r"第[一二三四五六七八九十百0-9]+节", clean):
            return clean[:80]
    return "章节待识别"


def _generate_textbook_id(filename: str) -> str:
    """Generate a textbook ID from filename.

    Uses Path(filename).stem to preserve prefixes like "01_局部解剖学".
    Kept as internal helper for backward compatibility with existing chunk IDs.
    """
    stem = Path(filename).stem
    cleaned = re.sub(r"[^\w]", "_", stem)
    cleaned = re.sub(r"_+", "_", cleaned)
    cleaned = cleaned.strip("_")
    if len(cleaned) < 3:
        hash_suffix = hashlib.md5(filename.encode()).hexdigest()[:8]
        return f"book_{hash_suffix}"
    id_part = cleaned[:20]
    return f"book_{id_part}"


def parse_single_file(file_path: Path, max_pages: int | None = None) -> dict[str, Any]:
    """Parse a single file and return structured data."""
    result = parse_document(file_path, max_pages=max_pages)

    # Assign textbook_id
    result["textbook_id"] = _generate_textbook_id(result["filename"])

    # Assign book title
    result["title"] = infer_book_name(result["filename"])

    return result


def parse_textbook_files(
    source_dir: Path,
    filenames: list[str] | None = None,
    max_pages: int | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Parse textbook files from source directory.

    Returns:
        - List of successfully parsed textbooks
        - List of errors (dicts with filename and error message)
    """
    store = TextbookStore()
    textbooks = []
    errors = []

    if filenames:
        # Parse specific files
        for fname in filenames:
            file_path = source_dir / fname
            if not file_path.exists():
                errors.append({"filename": fname, "error": "File not found"})
                continue

            result = parse_single_file(file_path, max_pages=max_pages)
            if result["parse_status"] == "failed":
                errors.append({"filename": fname, "error": result.get("error", "Unknown error")})
            else:
                store.save(result)
                textbooks.append(result)
    else:
        # Discover and parse all supported files
        if not source_dir.exists():
            return [], [{"filename": str(source_dir), "error": "Directory not found"}]

        for ext in ["*.pdf", "*.md", "*.txt", "*.docx"]:
            for file_path in source_dir.glob(ext):
                result = parse_single_file(file_path, max_pages=max_pages)
                if result["parse_status"] == "failed":
                    errors.append({"filename": file_path.name, "error": result.get("error", "Unknown error")})
                else:
                    store.save(result)
                    textbooks.append(result)

    return textbooks, errors


def build_chunks_from_parsed_textbooks(
    textbook_ids: list[str] | None = None,
    chunk_size: int = 700,
    chunk_overlap: int = 80,
) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Build chunks from parsed textbooks.

    Args:
        textbook_ids: List of textbook IDs to process, or None for all
        chunk_size: Target chunk size in characters
        chunk_overlap: Overlap between chunks

    Returns:
        - List of chunk dictionaries
        - List of error messages
    """
    store = TextbookStore()
    settings = get_settings()
    all_chunks = []
    errors = []

    if textbook_ids is None:
        # Load all parsed textbooks
        all_textbooks = store.list_all()
        textbook_ids = [t["textbook_id"] for t in all_textbooks]

    for tid in textbook_ids:
        data = store.load(tid)
        if not data:
            errors.append(f"Textbook {tid} not found in store")
            continue

        filename = data.get("filename", "")
        book_title = data.get("title", infer_book_name(filename))

        # Process chapters as primary content unit
        chapters = data.get("chapters", [])
        for ch in chapters:
            if not ch.get("content", "").strip():
                continue

            page_start = ch.get("page_start", 0)
            page_end = ch.get("page_end", page_start)
            chapter_title = ch.get("title", "章节待识别")

            # Chunk the chapter content
            text_chunks = chunk_text(ch["content"], chunk_size=chunk_size, overlap=chunk_overlap)

            for local_idx, text in enumerate(text_chunks, start=1):
                chunk_id = f"{tid}_{ch['chapter_id']}_c{local_idx}"
                all_chunks.append({
                    "chunk_id": chunk_id,
                    "textbook_id": tid,
                    "book": book_title,
                    "source_file": filename,
                    "chapter": chapter_title,
                    "page_start": page_start,
                    "page_end": page_end,
                    "text": text,
                    "char_count": len(text),
                    "evidence_ids": [],
                })

    return all_chunks, errors


def build_chunks_from_textbooks(max_pages_per_pdf: int | None = None) -> tuple[list[dict], list[str]]:
    """
    Legacy function for building chunks directly from PDF files.

    This is used by the existing index build pipeline.
    """
    from .pdf_loader import load_textbook_pages

    settings = get_settings()
    pages, errors = load_textbook_pages(settings.textbook_dir, max_pages_per_pdf=max_pages_per_pdf)

    for page in pages:
        page["book"] = infer_book_name(page.get("source_file", ""))
        page["chapter"] = infer_chapter(page.get("text", ""))
        page["section"] = ""

    chunks = _pages_to_chunks(pages, chunk_size=settings.chunk_size, overlap=settings.chunk_overlap)

    for chunk in chunks:
        chunk["book"] = infer_book_name(chunk.get("source_file", ""))
        chunk["chapter"] = chunk.get("chapter") or "章节待识别"
        chunk["section"] = chunk.get("section") or ""
        chunk["char_count"] = len(chunk.get("text", ""))

    return chunks, errors


def _pages_to_chunks(
    pages: list[dict],
    chunk_size: int = 700,
    overlap: int = 80,
) -> list[dict]:
    """Convert pages to chunks with overlap."""
    chunks = []
    for page in pages:
        page_text = page.get("text", "")
        if not page_text.strip():
            continue

        text_parts = []
        current = []
        current_len = 0

        for line in page_text.split("\n"):
            line = line.strip()
            if not line:
                if current:
                    text_parts.append("\n".join(current))
                    current = []
                    current_len = 0
                continue

            if current_len + len(line) > chunk_size and current:
                text_parts.append("\n".join(current))
                # Keep overlap
                overlap_text = "\n".join(current)[-overlap:]
                current = [overlap_text, line]
                current_len = len(overlap_text) + len(line)
            else:
                current.append(line)
                current_len += len(line)

        if current:
            text_parts.append("\n".join(current))

        for local_idx, text in enumerate(text_parts, start=1):
            if not text.strip():
                continue
            chunk_id = f"{page['source_file']}::p{page['page']}::c{local_idx}"
            chunks.append({
                "text": text.strip(),
                "source_file": page["source_file"],
                "page": page["page"],
                "chunk_id": chunk_id,
            })

    return chunks
