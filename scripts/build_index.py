from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.chunker import pages_to_chunks  # noqa: E402
from src.config import get_embedding_config, get_settings, list_pdf_files  # noqa: E402
from src.pdf_loader import load_textbook_pages  # noqa: E402
from src.vector_store import VectorStore  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build HealthPDF Agent retrieval index.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing index.")
    parser.add_argument("--debug", action="store_true", help="Debug mode; limit pages if provided.")
    parser.add_argument("--max-pages-per-pdf", type=int, default=None, help="Limit pages per PDF.")
    parser.add_argument("--backend", choices=["hybrid", "embedding", "tfidf"], default="hybrid")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = get_settings()
    start_time = time.time()

    pdf_files = list_pdf_files(settings.textbook_dir)
    if not settings.textbook_dir.exists():
        print("未发现 textbooks/ 教材目录。")
        return 1
    if not pdf_files:
        print("未发现教材 PDF。")
        return 1
    if settings.index_file.exists() and not args.force and not args.debug:
        print(f"索引已存在：{settings.index_file}")
        print("如需重建，请添加 --force。")
        return 0

    max_pages = args.max_pages_per_pdf if args.debug or args.max_pages_per_pdf else None
    pages, errors = load_textbook_pages(settings.textbook_dir, max_pages_per_pdf=max_pages)
    chunks = pages_to_chunks(pages, chunk_size=1000, overlap=150)
    if not chunks:
        print("未提取到可索引文本。")
        return 1

    store = VectorStore(settings.index_file)
    metadata = store.build_index(
        chunks,
        use_embedding=args.backend in {"hybrid", "embedding"},
        backend=args.backend,
        pdf_files=[path.name for path in pdf_files],
        chunk_size=1000,
        overlap=150,
    )
    store.save_index(settings.index_file)

    elapsed = time.time() - start_time
    if metadata.get("embedding_warning"):
        print(f"warning: {metadata['embedding_warning']}")
    if errors:
        print(f"warning: {len(errors)} 个 PDF 读取异常，已跳过异常页或文件。")

    print(f"PDF 数量: {len(pdf_files)}")
    print(f"总页数: {len(pages)}")
    print(f"chunk 数量: {len(chunks)}")
    print(f"是否构建 TF-IDF: {store.has_tfidf}")
    print(f"是否构建 embedding: {store.has_embedding}")
    print(f"embedding model: {get_embedding_config()['model']}")
    print(f"索引保存路径: {settings.index_file}")
    print(f"总耗时: {elapsed:.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
