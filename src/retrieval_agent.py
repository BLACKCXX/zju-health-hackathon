from __future__ import annotations

from collections import defaultdict

from .config import get_settings
from .parser_agent import infer_book_name
from .vector_store import VectorStore


def to_evidence(item: dict, index: int = 0) -> dict:
    source_file = item.get("source_file", "")
    text = item.get("text", "")
    return {
        "evidence_id": item.get("evidence_id") or f"ev_{index + 1:03d}",
        "book": item.get("book") or infer_book_name(source_file),
        "source_file": source_file,
        "chapter": item.get("chapter") or "章节待识别",
        "section": item.get("section") or "",
        "page": int(item.get("page") or 0),
        "quote": text[:260],
        "text": text,
        "chunk_id": item.get("chunk_id", ""),
        "score": float(item.get("score") or 0.0),
        "match_type": item.get("match_type") or "tfidf",
    }


class RetrievalAgent:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _load_store(self) -> VectorStore | None:
        if not self.settings.index_file.exists():
            return None
        return VectorStore.load_index(self.settings.index_file)

    def search(self, query: str, top_k: int | None = None) -> list[dict]:
        store = self._load_store()
        if store is None:
            return []
        limit = top_k or self.settings.rag_top_k
        backend = self.settings.retrieval_backend
        if backend == "tfidf":
            rows = store.search_tfidf(query, top_k=limit)
        elif backend == "embedding":
            rows = store.search_embedding(query, top_k=limit) or store.search_tfidf(query, top_k=limit)
        else:
            rows = store.search_hybrid(query, query, [], top_k=limit)
        return [to_evidence(row, idx) for idx, row in enumerate(rows)]

    def search_by_book(self, topic: str, per_book_k: int = 5) -> list[dict]:
        rows = self.search(topic, top_k=max(per_book_k * 10, 30))
        grouped: dict[str, list[dict]] = defaultdict(list)
        for row in rows:
            if len(grouped[row["book"]]) < per_book_k:
                grouped[row["book"]].append(row)
        evidence: list[dict] = []
        for items in grouped.values():
            evidence.extend(items)
        for idx, item in enumerate(evidence):
            item["evidence_id"] = f"ev_{idx + 1:03d}"
        return evidence

    def search_for_graph(self, topic: str, per_book_k: int | None = None, global_top_k: int | None = None) -> list[dict]:
        per_book = per_book_k or self.settings.graph_top_k_per_book
        global_k = global_top_k or self.settings.graph_global_top_k
        merged: dict[str, dict] = {}
        for item in self.search_by_book(topic, per_book_k=per_book) + self.search(topic, top_k=global_k):
            key = item.get("chunk_id") or f"{item['source_file']}:{item['page']}:{item['quote'][:20]}"
            merged[key] = item
        evidence = list(merged.values())[:global_k]
        for idx, item in enumerate(evidence):
            item["evidence_id"] = f"ev_{idx + 1:03d}"
        return evidence

    def search_for_node_detail(self, node_name: str, graph_context: dict | None = None) -> list[dict]:
        topic = graph_context.get("topic", "") if graph_context else ""
        return self.search(f"{topic} {node_name}", top_k=self.settings.rag_top_k)

    def search_for_report(self, topic: str, graph_state: dict | None = None) -> list[dict]:
        if graph_state and graph_state.get("evidence"):
            return graph_state["evidence"]
        return self.search_for_graph(topic)
