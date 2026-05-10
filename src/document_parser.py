from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import fitz

SUPPORTED_FORMATS = {".pdf", ".md", ".txt"}


def clean_title(title: str) -> str:
    """Clean a chapter title by removing noise and invalid characters."""
    if not title:
        return ""
    # Remove form feed and replacement characters
    title = title.replace("\x08", "").replace("\xef\xbf\xbd", "").replace("\x00", "")
    # Normalize whitespace
    title = re.sub(r"[ \t\r\f\v]+", " ", title)
    title = re.sub(r"\n+", " ", title)
    # Remove trailing page numbers (digits at the end that look like page refs)
    title = re.sub(r"\s+\d+$", "", title)
    # Remove leading/trailing punctuation and spaces
    title = title.strip().strip(".,，、；;:：!?！？\"")
    return title


def is_valid_chapter_title(title: str) -> bool:
    """Check if a title is a valid chapter heading (not noise)."""
    if not title or len(title) < 2:
        return False
    cleaned = clean_title(title)
    if not cleaned or len(cleaned) < 2:
        return False
    if len(cleaned) > 80:
        return False
    if cleaned.count("\xef\xbf\xbd") > 1:
        return False
    bad_patterns = [
        r"第\s*\d+\s*页\s*/\s*共\s*\d+\s*页",
        r"Page\s*\d+\s*of\s*\d+",
        r"AI\s*全栈极速黑客",
        r"赛题文档",
        r"^\d+\s*$",
        r"^[第\s\d]+页",
    ]
    for pattern in bad_patterns:
        if re.search(pattern, cleaned):
            return False
    text_chars = len(re.findall(r"[一-￿A-Za-z]", cleaned))
    if text_chars < 2:
        return False
    punct_ratio = len(re.findall(r"[，、；：。，、]", cleaned)) / max(len(cleaned), 1)
    if punct_ratio > 0.4 and len(cleaned) > 10:
        return False
    noise_terms = ["目录", "版权", "前言", "序言", "附录", "参考文献", "索引"]
    if cleaned in noise_terms:
        return False
    return True


def generate_textbook_id(filename: str) -> str:
    """Generate a stable textbook_id from filename.
    Uses the stem (filename without extension) to maintain backward
    compatibility with existing stored files.
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


def _clean_text(text: str) -> str:
    """Normalize whitespace and remove null bytes."""
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_toc_from_pdf(doc: fitz.Document) -> list:
    """Extract table of contents from PDF using doc.get_toc()."""
    try:
        toc = doc.get_toc(simple=False)
        if not toc:
            return []
        result = []
        for entry in toc:
            if len(entry) < 3:
                continue
            level = int(entry[0])
            title = str(entry[1])
            page = int(entry[2])
            if level <= 3 and page > 0:
                cleaned_title = clean_title(title)
                if is_valid_chapter_title(cleaned_title):
                    result.append((level, cleaned_title, page))
        return result
    except Exception:
        return []


def _extract_chapters_from_toc(toc: list, total_pages: int) -> list:
    """Build chapter structure from TOC entries."""
    chapters = []
    for idx, (level, title, page_start) in enumerate(toc):
        if idx + 1 < len(toc):
            page_end = toc[idx + 1][2] - 1
        else:
            page_end = total_pages
        if page_end < page_start:
            page_end = page_start
        chapters.append({
            "chapter_id": f"ch_{len(chapters) + 1:03d}",
            "title": title,
            "page_start": page_start,
            "page_end": page_end,
        })
    return chapters


def parse_pdf(path: Path, max_pages: int | None = None) -> dict:
    """Parse a PDF file and return structured textbook data."""
    result = {
        "textbook_id": "",
        "filename": path.name,
        "title": path.stem,
        "format": "pdf",
        "total_pages": 0,
        "total_chars": 0,
        "chapters": [],
        "pages": [],
        "parse_status": "pending",
        "error": "",
    }

    try:
        with fitz.open(path) as doc:
            total = len(doc)
            result["total_pages"] = total

            toc = _extract_toc_from_pdf(doc)

            if toc:
                chapters_from_toc = _extract_chapters_from_toc(toc, total)

                all_pages_text = []
                for page_idx in range(total):
                    page = doc[page_idx]
                    text = page.get_text("text") or ""
                    text = _clean_text(text)
                    all_pages_text.append((page_idx + 1, text))

                for ch in chapters_from_toc:
                    content_parts = []
                    char_count = 0
                    for page_num, page_text in all_pages_text:
                        if ch["page_start"] <= page_num <= ch["page_end"]:
                            if page_text.strip():
                                content_parts.append(page_text)
                                char_count += len(page_text)
                    ch["content"] = "\n\n".join(content_parts)
                    ch["char_count"] = char_count

                result["chapters"] = chapters_from_toc

                result["pages"] = [
                    {"page": i + 1, "chapter": "", "text": all_pages_text[i][1], "char_count": len(all_pages_text[i][1])}
                    for i in range(total) if all_pages_text[i][1].strip()
                ]

                result["total_chars"] = sum(len(p["text"]) for p in result["pages"])
                result["parse_status"] = "completed"

            else:
                pages_to_process = total if max_pages is None else min(total, max_pages)

                all_pages_text = []
                current_chapter_title = "未识别章节"
                chapter_pages = []

                for page_idx in range(pages_to_process):
                    page = doc[page_idx]
                    text = page.get_text("text") or ""
                    text = _clean_text(text)

                    if not text.strip():
                        continue

                    all_pages_text.append((page_idx + 1, text))

                    lines = text.split("\n")[:8]
                    found_heading = None
                    for line in lines:
                        stripped = line.strip()
                        if not stripped:
                            continue
                        # Try to combine with next line if this looks like a chapter start
                        combined = stripped
                        next_line_idx = lines.index(line) + 1
                        if next_line_idx < len(lines):
                            next_line = lines[next_line_idx].strip()
                            if next_line and is_valid_chapter_title(stripped + " " + next_line[:20]):
                                combined = stripped + " " + next_line[:20]

                        for pattern in [
                            r"^第[一二三四五六七八九十百零\d]+章",
                            r"^第[一二三四五六七八九十百零\d]+节",
                        ]:
                            m = re.search(pattern, combined)
                            if m:
                                title = combined[:80]
                                # "第X节" without proper combining is usually just section entry
                                # Only accept "第X节" if it's combined with meaningful next line content
                                if m.group(0).endswith("节"):
                                    # Check if next line provides actual chapter content (not just page number)
                                    if next_line_idx < len(lines):
                                        next_line_clean = lines[next_line_idx].strip()
                                        if next_line_clean and len(next_line_clean) > 2 and not next_line_clean[0].isdigit():
                                            if is_valid_chapter_title(title):
                                                found_heading = title
                                else:
                                    if is_valid_chapter_title(title):
                                        found_heading = title
                                break
                        if found_heading:
                            break

                    if found_heading:
                        current_chapter_title = found_heading

                    chapter_pages.append((page_idx + 1, current_chapter_title, text))

                chapters_dict = {}
                for page_num, ch_title, page_text in chapter_pages:
                    if ch_title not in chapters_dict:
                        chapters_dict[ch_title] = {
                            "chapter_id": f"ch_{len(chapters_dict) + 1:03d}",
                            "title": ch_title,
                            "page_start": page_num,
                            "page_end": page_num,
                            "content": page_text,
                            "char_count": len(page_text),
                        }
                    else:
                        chapters_dict[ch_title]["page_end"] = page_num
                        chapters_dict[ch_title]["content"] += "\n\n" + page_text
                        chapters_dict[ch_title]["char_count"] += len(page_text)

                result["chapters"] = list(chapters_dict.values())
                result["pages"] = [
                    {"page": p[0], "chapter": p[1], "text": p[2], "char_count": len(p[2])}
                    for p in chapter_pages
                ]
                result["total_chars"] = sum(len(p[2]) for p in chapter_pages)
                result["parse_status"] = "completed"

    except Exception as exc:
        result["parse_status"] = "failed"
        result["error"] = str(exc)

    return result


def parse_markdown(path: Path) -> dict:
    """Parse a Markdown file and return structured textbook data."""
    result = {
        "textbook_id": "",
        "filename": path.name,
        "title": path.stem,
        "format": "md",
        "total_pages": 0,
        "total_chars": 0,
        "chapters": [],
        "parse_status": "pending",
        "error": "",
    }

    try:
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw_text = f.read()
        except UnicodeDecodeError:
            with open(path, "r", encoding="gbk") as f:
                raw_text = f.read()

        text = _clean_text(raw_text)
        result["total_chars"] = len(text)

        lines = text.split("\n")
        chapters = []
        current_content = []
        current_title = "全文"
        chapter_idx = 0

        for line in lines:
            stripped = line.strip()
            m = re.match(r"^(#{1,4})\s+(.+)", stripped)
            if m:
                if current_content:
                    chapter_idx += 1
                    chapters.append({
                        "chapter_id": f"ch_{chapter_idx:03d}",
                        "title": clean_title(current_title) if current_title else f"第 {chapter_idx} 节",
                        "page_start": chapter_idx,
                        "page_end": chapter_idx,
                        "content": "\n".join(current_content).strip(),
                        "char_count": sum(len(c) for c in current_content),
                    })
                    current_content = []
                current_title = m.group(2).strip()[:80]
            else:
                if stripped:
                    current_content.append(stripped)

        if current_content:
            chapter_idx += 1
            chapters.append({
                "chapter_id": f"ch_{chapter_idx:03d}",
                "title": clean_title(current_title) if current_title else f"第 {chapter_idx} 节",
                "page_start": chapter_idx,
                "page_end": chapter_idx,
                "content": "\n".join(current_content).strip(),
                "char_count": sum(len(c) for c in current_content),
            })

        if not chapters:
            chapters.append({
                "chapter_id": "ch_001",
                "title": "全文",
                "page_start": 1,
                "page_end": 1,
                "content": text,
                "char_count": len(text),
            })

        result["chapters"] = chapters
        result["parse_status"] = "completed"

    except Exception as exc:
        result["parse_status"] = "failed"
        result["error"] = str(exc)

    return result


def parse_txt(path: Path) -> dict:
    """Parse a TXT file and return structured textbook data."""
    result = {
        "textbook_id": "",
        "filename": path.name,
        "title": path.stem,
        "format": "txt",
        "total_pages": 0,
        "total_chars": 0,
        "chapters": [],
        "parse_status": "pending",
        "error": "",
    }

    try:
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw_text = f.read()
        except UnicodeDecodeError:
            with open(path, "r", encoding="gbk") as f:
                raw_text = f.read()

        text = _clean_text(raw_text)
        result["total_chars"] = len(text)

        lines = text.split("\n")
        chapters = []
        current_content = []
        current_title = ""
        chapter_idx = 0

        chapter_patterns = [
            r"^第[一二三四五六七八九十百零\d]+章\s*",
            r"^第[一二三四五六七八九十百零\d]+节\s*",
            r"^Chapter\s+\d+[\s:。：]",
        ]

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            is_heading = False
            for pattern in chapter_patterns:
                if re.match(pattern, stripped):
                    is_heading = True
                    break

            if is_heading:
                if current_content:
                    chapter_idx += 1
                    title = clean_title(current_title) if current_title else f"第 {chapter_idx} 节"
                    if not is_valid_chapter_title(title):
                        title = f"第 {chapter_idx} 节"
                    chapters.append({
                        "chapter_id": f"ch_{chapter_idx:03d}",
                        "title": title,
                        "page_start": chapter_idx,
                        "page_end": chapter_idx,
                        "content": "\n".join(current_content).strip(),
                        "char_count": sum(len(c) for c in current_content),
                    })
                    current_content = []

                current_title = stripped[:80]
            else:
                current_content.append(stripped)

        if current_content:
            chapter_idx += 1
            title = clean_title(current_title) if current_title else f"第 {chapter_idx} 节"
            if not is_valid_chapter_title(title):
                title = f"第 {chapter_idx} 节"
            chapters.append({
                "chapter_id": f"ch_{chapter_idx:03d}",
                "title": title,
                "page_start": chapter_idx,
                "page_end": chapter_idx,
                "content": "\n".join(current_content).strip(),
                "char_count": sum(len(c) for c in current_content),
            })

        if not chapters:
            chapters.append({
                "chapter_id": "ch_001",
                "title": "全文",
                "page_start": 1,
                "page_end": 1,
                "content": text,
                "char_count": len(text),
            })

        result["chapters"] = chapters
        result["parse_status"] = "completed"

    except Exception as exc:
        result["parse_status"] = "failed"
        result["error"] = str(exc)

    return result


def parse_document(path: Path, max_pages: int | None = None) -> dict:
    """Parse a document based on its extension."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return parse_pdf(path, max_pages)
    elif suffix == ".md":
        return parse_markdown(path)
    elif suffix == ".txt":
        return parse_txt(path)
    else:
        return {
            "textbook_id": "",
            "filename": path.name,
            "title": path.stem,
            "format": suffix,
            "total_pages": 0,
            "total_chars": 0,
            "chapters": [],
            "parse_status": "failed",
            "error": f"Unsupported format: {suffix}",
        }


BOOK_NAME_MAP = {
    "01_局部解剖学.pdf": "局部解剖学",
    "02_组织学与胚胎学.pdf": "组织学与胚胎学",
    "03_生理学.pdf": "生理学",
    "04_医学微生物学.pdf": "医学微生物学",
    "05_病理学.pdf": "病理学",
    "06_传染病学.pdf": "传染病学",
    "07_病理生理学.pdf": "病理生理学",
}


def infer_book_title(filename: str) -> str:
    """Infer book title from filename."""
    if filename in BOOK_NAME_MAP:
        return BOOK_NAME_MAP[filename]
    name = re.sub(r"^\d+_", "", filename)
    name = re.sub(r"\.(pdf|md|txt)$", "", name, flags=re.IGNORECASE)
    return name.strip()