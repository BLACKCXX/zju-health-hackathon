from __future__ import annotations

from pathlib import Path

import fitz


def list_pdfs(pdf_dir: Path) -> list[Path]:
    if not pdf_dir.exists():
        return []
    return sorted(pdf_dir.rglob("*.pdf"))


def load_pdf_pages(pdf_path: Path, max_pages: int | None = None) -> list[dict]:
    pages: list[dict] = []
    with fitz.open(pdf_path) as doc:
        page_count = len(doc) if max_pages is None else min(len(doc), max_pages)
        for page_index in range(page_count):
            page = doc[page_index]
            text = page.get_text("text") or ""
            if text.strip():
                pages.append(
                    {
                        "source_file": pdf_path.name,
                        "source_path": str(pdf_path),
                        "page": page_index + 1,
                        "text": text,
                    }
                )
    return pages


def load_textbook_pages(
    pdf_dir: Path,
    max_pages_per_pdf: int | None = None,
) -> tuple[list[dict], list[str]]:
    all_pages: list[dict] = []
    errors: list[str] = []
    for pdf_path in list_pdfs(pdf_dir):
        try:
            all_pages.extend(load_pdf_pages(pdf_path, max_pages=max_pages_per_pdf))
        except Exception as exc:
            errors.append(f"{pdf_path.name}: {exc}")
    return all_pages, errors
