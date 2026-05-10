from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import get_settings

BOOK_NAME_MAP = {
    "01_局部解剖学.pdf": "局部解剖学",
    "02_组织学与胚胎学.pdf": "组织学与胚胎学",
    "03_生理学.pdf": "生理学",
    "04_医学微生物学.pdf": "医学微生物学",
    "05_病理学.pdf": "病理学",
    "06_传染病学.pdf": "传染病学",
    "07_病理生理学.pdf": "病理生理学",
}


def infer_book_title(source_file: str) -> str:
    """Infer book title from source filename."""
    if source_file in BOOK_NAME_MAP:
        return BOOK_NAME_MAP[source_file]
    import re
    name = re.sub(r"^\d+_", "", source_file)
    name = re.sub(r"\.(pdf|md|txt)$", "", name, flags=re.IGNORECASE)
    return name.strip()


class TextbookStore:
    """Manages parsed textbook data stored as JSON."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.data_dir = self.settings.base_dir / "data" / "parsed"
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _get_store_file(self, textbook_id: str) -> Path:
        return self.data_dir / f"{textbook_id}.json"

    def save(self, textbook_data: dict[str, Any]) -> bool:
        """Save textbook data to JSON file."""
        textbook_id = textbook_data.get("textbook_id", "")
        if not textbook_id:
            return False
        try:
            # Assign book title from filename
            source_file = textbook_data.get("filename", "")
            if not textbook_data.get("title"):
                textbook_data["title"] = infer_book_title(source_file)

            store_path = self._get_store_file(textbook_id)
            with open(store_path, "w", encoding="utf-8") as f:
                json.dump(textbook_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def load(self, textbook_id: str) -> dict[str, Any] | None:
        """Load textbook data from JSON file."""
        store_path = self._get_store_file(textbook_id)
        if not store_path.exists():
            return None
        try:
            with open(store_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def list_all(self) -> list[dict[str, Any]]:
        """List all stored textbooks."""
        textbooks = []
        if not self.data_dir.exists():
            return textbooks
        for json_file in self.data_dir.glob("*.json"):
            data = self.load(json_file.stem)
            if data:
                # Return summary without full content
                summary = {k: v for k, v in data.items() if k != "pages"}
                summary["chapter_count"] = len(data.get("chapters", []))
                textbooks.append(summary)
        return textbooks

    def get_chapters(self, textbook_id: str) -> list[dict[str, Any]]:
        """Get chapters for a specific textbook."""
        data = self.load(textbook_id)
        if not data:
            return []
        return data.get("chapters", [])

    def get_pages(self, textbook_id: str) -> list[dict[str, Any]]:
        """Get pages for a specific textbook."""
        data = self.load(textbook_id)
        if not data:
            return []
        return data.get("pages", [])

    def exists(self, textbook_id: str) -> bool:
        """Check if a textbook exists in store."""
        return self._get_store_file(textbook_id).exists()