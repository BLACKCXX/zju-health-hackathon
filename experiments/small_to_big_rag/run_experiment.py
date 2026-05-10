"""Offline Small-to-Big RAG retrieval experiment.

The script reads parsed textbook JSON files or small demo documents, builds
local TF-IDF indexes, evaluates three retrieval strategies, and writes all
outputs under experiments/small_to_big_rag/results/.
"""

from __future__ import annotations

import csv
import hashlib
import json
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parents[1]
RESULTS_DIR = BASE_DIR / "results"
QUESTIONS_PATH = BASE_DIR / "eval_questions.json"


@dataclass(frozen=True)
class Strategy:
    name: str
    chunk_size: int | None = None
    overlap: int | None = None
    top_k: int = 5
    small_chunk_size: int | None = None
    small_overlap: int | None = None
    parent_chunk_size: int | None = None
    parent_overlap: int | None = None


STRATEGIES = [
    Strategy("baseline_medium", chunk_size=700, overlap=80, top_k=5),
    Strategy("small_only", chunk_size=300, overlap=50, top_k=5),
    Strategy(
        "small_to_big",
        top_k=5,
        small_chunk_size=300,
        small_overlap=50,
        parent_chunk_size=1200,
        parent_overlap=150,
    ),
]


def clean_text(text: str) -> str:
    return " ".join((text or "").replace("\x00", " ").split())


def stable_id(*parts: Any) -> str:
    raw = "::".join(str(part) for part in parts)
    return hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()[:16]


def load_corpus() -> list[dict[str, Any]]:
    """Load chapter/page-like document fragments from parsed textbooks.

    Returned docs preserve source metadata needed by citation and parent mapping.
    """

    docs: list[dict[str, Any]] = []
    parsed_dir = PROJECT_ROOT / "data" / "parsed"
    parsed_files = sorted(parsed_dir.glob("*.json")) if parsed_dir.exists() else []

    for path in parsed_files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"[WARN] skip unreadable parsed file {path}: {exc}")
            continue

        textbook_id = data.get("textbook_id") or path.stem
        textbook = data.get("title") or data.get("textbook") or path.stem
        filename = data.get("filename") or path.name

        chapters = data.get("chapters") or []
        for chapter_index, chapter in enumerate(chapters):
            content = clean_text(chapter.get("content") or chapter.get("text") or "")
            if len(content) < 20:
                continue
            chapter_id = chapter.get("chapter_id") or f"ch_{chapter_index + 1:03d}"
            page_start = chapter.get("page_start") or chapter.get("page") or None
            page_end = chapter.get("page_end") or page_start
            docs.append(
                {
                    "text": content,
                    "textbook_id": textbook_id,
                    "textbook": textbook,
                    "filename": filename,
                    "chapter": chapter.get("title") or chapter_id,
                    "chapter_id": chapter_id,
                    "page_start": page_start,
                    "page_end": page_end,
                    "source_id": f"{textbook_id}:{chapter_id}",
                    "source_path": str(path.relative_to(PROJECT_ROOT)),
                }
            )

        pages = data.get("pages") or []
        if not chapters and pages:
            for page_index, page in enumerate(pages):
                content = clean_text(page.get("content") or page.get("text") or "")
                if len(content) < 20:
                    continue
                page_no = page.get("page") or page.get("page_number") or page_index + 1
                docs.append(
                    {
                        "text": content,
                        "textbook_id": textbook_id,
                        "textbook": textbook,
                        "filename": filename,
                        "chapter": page.get("chapter") or "page",
                        "chapter_id": page.get("chapter_id") or f"page_{page_no}",
                        "page_start": page_no,
                        "page_end": page_no,
                        "source_id": f"{textbook_id}:page_{page_no}",
                        "source_path": str(path.relative_to(PROJECT_ROOT)),
                    }
                )

    if docs:
        return docs

    fallbacks = [
        PROJECT_ROOT / "data" / "sample_docs" / "sample_health_knowledge.md",
        PROJECT_ROOT / "report" / "sample_integration_炎症.md",
    ]
    for path in fallbacks:
        if not path.exists():
            continue
        content = clean_text(path.read_text(encoding="utf-8", errors="ignore"))
        if not content:
            continue
        docs.append(
            {
                "text": content,
                "textbook_id": "demo",
                "textbook": path.stem,
                "filename": path.name,
                "chapter": "demo",
                "chapter_id": "demo",
                "page_start": None,
                "page_end": None,
                "source_id": f"demo:{path.stem}",
                "source_path": str(path.relative_to(PROJECT_ROOT)),
            }
        )
        break

    return docs


def make_chunks(docs: list[dict[str, Any]], chunk_size: int, overlap: int) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    step = max(1, chunk_size - overlap)
    for doc_index, doc in enumerate(docs):
        text = doc["text"]
        if not text:
            continue
        start = 0
        while start < len(text):
            end = min(len(text), start + chunk_size)
            chunk_text = text[start:end]
            if len(chunk_text.strip()) >= 10:
                chunk = {
                    "chunk_id": stable_id(doc["source_id"], start, end, chunk_size, overlap),
                    "text": chunk_text,
                    "char_start": start,
                    "char_end": end,
                    "doc_index": doc_index,
                    **{k: v for k, v in doc.items() if k != "text"},
                }
                chunks.append(chunk)
            if end >= len(text):
                break
            start += step
    return chunks


def build_tfidf_index(chunks: list[dict[str, Any]]):
    if not chunks:
        raise RuntimeError("No chunks available for TF-IDF index.")
    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), lowercase=False)
    matrix = vectorizer.fit_transform([chunk["text"] for chunk in chunks])
    return vectorizer, matrix


def search_tfidf(
    query: str,
    chunks: list[dict[str, Any]],
    vectorizer: TfidfVectorizer,
    matrix,
    top_k: int,
) -> list[dict[str, Any]]:
    query_vector = vectorizer.transform([query])
    scores = cosine_similarity(query_vector, matrix).ravel()
    ranked = scores.argsort()[::-1][:top_k]
    results = []
    for rank, idx in enumerate(ranked, start=1):
        item = dict(chunks[int(idx)])
        item["score"] = float(scores[int(idx)])
        item["rank"] = rank
        results.append(item)
    return results


def build_parent_chunks(
    docs: list[dict[str, Any]],
    parent_chunk_size: int,
    parent_overlap: int,
) -> list[dict[str, Any]]:
    return make_chunks(docs, parent_chunk_size, parent_overlap)


def ranges_overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return max(a_start, b_start) < min(a_end, b_end)


def map_small_to_parent(
    small_chunk: dict[str, Any],
    parent_chunks: list[dict[str, Any]],
) -> dict[str, Any]:
    same_source = [
        parent
        for parent in parent_chunks
        if parent.get("source_id") == small_chunk.get("source_id")
        and ranges_overlap(
            int(small_chunk["char_start"]),
            int(small_chunk["char_end"]),
            int(parent["char_start"]),
            int(parent["char_end"]),
        )
    ]
    if same_source:
        midpoint = (small_chunk["char_start"] + small_chunk["char_end"]) / 2
        return min(
            same_source,
            key=lambda parent: abs(
                ((parent["char_start"] + parent["char_end"]) / 2) - midpoint
            ),
        )

    same_chapter = [
        parent
        for parent in parent_chunks
        if parent.get("textbook_id") == small_chunk.get("textbook_id")
        and parent.get("chapter_id") == small_chunk.get("chapter_id")
    ]
    if same_chapter:
        return same_chapter[0]

    return small_chunk


def citation_complete(context: dict[str, Any]) -> bool:
    return bool(context.get("textbook") and context.get("chapter")) and (
        context.get("page_start") is not None or context.get("page_end") is not None
    )


def context_payload(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "chunk_id": context.get("chunk_id"),
        "score": round(float(context.get("score", 0.0)), 6),
        "rank": context.get("rank"),
        "text": context.get("text", ""),
        "snippet": context.get("text", "")[:280],
        "textbook": context.get("textbook"),
        "filename": context.get("filename"),
        "chapter": context.get("chapter"),
        "chapter_id": context.get("chapter_id"),
        "page_start": context.get("page_start"),
        "page_end": context.get("page_end"),
        "source_id": context.get("source_id"),
    }


def compute_question_metrics(contexts: list[dict[str, Any]], expected_keywords: list[str]) -> dict[str, Any]:
    joined = "\n".join(context.get("text", "") for context in contexts)
    matched_keywords = [keyword for keyword in expected_keywords if keyword in joined]
    source_books = {
        context.get("textbook_id") or context.get("textbook")
        for context in contexts
        if context.get("textbook_id") or context.get("textbook")
    }
    citation_ratio = (
        sum(1 for context in contexts if citation_complete(context)) / len(contexts)
        if contexts
        else 0.0
    )
    return {
        "hit_at_5": 1.0 if matched_keywords else 0.0,
        "keyword_recall": len(matched_keywords) / max(1, len(expected_keywords)),
        "matched_keywords": matched_keywords,
        "context_chars": len(joined),
        "evidence_count": len(contexts),
        "source_diversity": len(source_books),
        "citation_completeness": citation_ratio,
    }


def evaluate_strategy(
    strategy: Strategy,
    questions: list[dict[str, Any]],
    indexes: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = []
    for question in questions:
        started = time.perf_counter()
        if strategy.name in {"baseline_medium", "small_only"}:
            chunks = indexes[strategy.name]["chunks"]
            vectorizer = indexes[strategy.name]["vectorizer"]
            matrix = indexes[strategy.name]["matrix"]
            contexts = search_tfidf(question["question"], chunks, vectorizer, matrix, strategy.top_k)
        else:
            small_hits = search_tfidf(
                question["question"],
                indexes["small_to_big"]["small_chunks"],
                indexes["small_to_big"]["small_vectorizer"],
                indexes["small_to_big"]["small_matrix"],
                strategy.top_k,
            )
            contexts = []
            seen_parent_ids: set[str] = set()
            for hit in small_hits:
                parent = dict(map_small_to_parent(hit, indexes["small_to_big"]["parent_chunks"]))
                parent["score"] = hit.get("score", 0.0)
                parent["rank"] = hit.get("rank")
                parent["matched_small_chunk_id"] = hit.get("chunk_id")
                parent_id = parent.get("chunk_id") or parent.get("matched_small_chunk_id")
                if parent_id in seen_parent_ids:
                    continue
                seen_parent_ids.add(parent_id)
                contexts.append(parent)

        latency_ms = (time.perf_counter() - started) * 1000
        metrics = compute_question_metrics(contexts, question.get("expected_keywords", []))
        rows.append(
            {
                "strategy": strategy.name,
                "question_id": question["id"],
                "question": question["question"],
                "expected_keywords": question.get("expected_keywords", []),
                "expected_topic": question.get("expected_topic"),
                "expected_book_hint": question.get("expected_book_hint"),
                "type": question.get("type"),
                "latency_ms": round(latency_ms, 3),
                **metrics,
                "contexts": [context_payload(context) for context in contexts],
            }
        )

    summary = {
        "strategy": strategy.name,
        "hit@5": statistics.fmean(row["hit_at_5"] for row in rows),
        "keyword_recall": statistics.fmean(row["keyword_recall"] for row in rows),
        "avg_context_chars": statistics.fmean(row["context_chars"] for row in rows),
        "avg_latency_ms": statistics.fmean(row["latency_ms"] for row in rows),
        "evidence_count": statistics.fmean(row["evidence_count"] for row in rows),
        "source_diversity": statistics.fmean(row["source_diversity"] for row in rows),
        "citation_completeness": statistics.fmean(row["citation_completeness"] for row in rows),
    }
    return rows, summary


def write_outputs(raw_results: list[dict[str, Any]], summaries: list[dict[str, Any]], metadata: dict[str, Any]) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    raw_payload = {"metadata": metadata, "results": raw_results}
    (RESULTS_DIR / "raw_results.json").write_text(
        json.dumps(raw_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary_payload = {"metadata": metadata, "strategies": summaries}
    (RESULTS_DIR / "summary.json").write_text(
        json.dumps(summary_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    fieldnames = [
        "strategy",
        "hit@5",
        "keyword_recall",
        "avg_context_chars",
        "avg_latency_ms",
        "evidence_count",
        "source_diversity",
        "citation_completeness",
    ]
    with (RESULTS_DIR / "results.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for summary in summaries:
            writer.writerow({key: round(summary[key], 4) if isinstance(summary[key], float) else summary[key] for key in fieldnames})

    lines = [
        "| 策略 | hit@5 | keyword_recall | avg_context_chars | avg_latency_ms | evidence_count | source_diversity | citation_completeness |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for summary in summaries:
        lines.append(
            "| {strategy} | {hit:.3f} | {recall:.3f} | {chars:.1f} | {latency:.2f} | {evidence:.2f} | {diversity:.2f} | {citation:.3f} |".format(
                strategy=summary["strategy"],
                hit=summary["hit@5"],
                recall=summary["keyword_recall"],
                chars=summary["avg_context_chars"],
                latency=summary["avg_latency_ms"],
                evidence=summary["evidence_count"],
                diversity=summary["source_diversity"],
                citation=summary["citation_completeness"],
            )
        )
    (RESULTS_DIR / "results_table.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    docs = load_corpus()
    if not docs:
        raise RuntimeError("No corpus documents found in data/parsed or fallback demo files.")

    print(f"Loaded {len(docs)} source docs.")

    indexes: dict[str, Any] = {}
    for strategy in STRATEGIES:
        if strategy.name in {"baseline_medium", "small_only"}:
            chunks = make_chunks(docs, strategy.chunk_size or 700, strategy.overlap or 80)
            vectorizer, matrix = build_tfidf_index(chunks)
            indexes[strategy.name] = {"chunks": chunks, "vectorizer": vectorizer, "matrix": matrix}
            print(f"Built {strategy.name}: {len(chunks)} chunks.")
        else:
            small_chunks = make_chunks(docs, strategy.small_chunk_size or 300, strategy.small_overlap or 50)
            parent_chunks = build_parent_chunks(docs, strategy.parent_chunk_size or 1200, strategy.parent_overlap or 150)
            small_vectorizer, small_matrix = build_tfidf_index(small_chunks)
            indexes[strategy.name] = {
                "small_chunks": small_chunks,
                "parent_chunks": parent_chunks,
                "small_vectorizer": small_vectorizer,
                "small_matrix": small_matrix,
            }
            print(f"Built {strategy.name}: {len(small_chunks)} small chunks, {len(parent_chunks)} parent chunks.")

    raw_results: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    for strategy in STRATEGIES:
        rows, summary = evaluate_strategy(strategy, questions, indexes)
        raw_results.extend(rows)
        summaries.append(summary)

    metadata = {
        "question_count": len(questions),
        "doc_count": len(docs),
        "source_paths": sorted({doc.get("source_path", "") for doc in docs if doc.get("source_path")}),
        "strategies": [strategy.__dict__ for strategy in STRATEGIES],
        "vectorizer": {"analyzer": "char_wb", "ngram_range": [2, 4], "lowercase": False},
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    write_outputs(raw_results, summaries, metadata)

    print("\nSummary:")
    for summary in summaries:
        print(
            "{strategy}: hit@5={hit:.3f}, recall={recall:.3f}, chars={chars:.1f}, latency={latency:.2f}ms, citation={citation:.3f}".format(
                strategy=summary["strategy"],
                hit=summary["hit@5"],
                recall=summary["keyword_recall"],
                chars=summary["avg_context_chars"],
                latency=summary["avg_latency_ms"],
                citation=summary["citation_completeness"],
            )
        )
    print(f"\nWrote results to {RESULTS_DIR.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
