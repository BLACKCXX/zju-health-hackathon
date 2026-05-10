from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import get_settings  # noqa: E402
from src.vector_store import VectorStore  # noqa: E402


def main() -> int:
    settings = get_settings()
    index_file = settings.index_file
    print(f"索引路径: {index_file}")
    if not index_file.exists():
        print("是否可加载: False")
        print("原因: 未发现索引缓存。")
        return 0

    try:
        store = VectorStore.load_index(index_file)
    except Exception as exc:
        print("是否可加载: False")
        print(f"原因: {exc}")
        return 1

    metadata = store.metadata
    print("是否可加载: True")
    print(f"chunk 数量: {len(store.chunks)}")
    print(f"是否有 embedding_matrix: {store.has_embedding}")
    print(f"是否有 tfidf_matrix: {store.has_tfidf}")
    print(f"embedding model: {metadata.get('embedding_model', '')}")
    print(f"构建时间: {metadata.get('created_at', '')}")
    print(f"retrieval backend: {metadata.get('retrieval_backend', '')}")
    print("PDF 文件列表:")
    for pdf_file in metadata.get("pdf_files", []):
        print(f"- {pdf_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
