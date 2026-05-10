from __future__ import annotations

import pickle
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize

from .config import get_embedding_config, get_settings
from .embedding_client import embed_query, embed_texts


class VectorStore:
    def __init__(self, index_file: Path | None = None) -> None:
        settings = get_settings()
        self.index_file = index_file or settings.index_file
        self.chunks: list[dict] = []
        self.tfidf_vectorizer: TfidfVectorizer | None = None
        self.tfidf_matrix: Any = None
        self.embedding_matrix: np.ndarray | None = None
        self.metadata: dict = {}

    @property
    def has_tfidf(self) -> bool:
        return self.tfidf_vectorizer is not None and self.tfidf_matrix is not None

    @property
    def has_embedding(self) -> bool:
        return self.embedding_matrix is not None and self.embedding_matrix.size > 0

    @property
    def is_ready(self) -> bool:
        return bool(self.chunks) and (self.has_tfidf or self.has_embedding)

    @property
    def built_at(self) -> str | None:
        return self.metadata.get("created_at")

    def build_index(
        self,
        chunks: list[dict],
        use_embedding: bool = True,
        backend: str | None = None,
        pdf_files: list[str] | None = None,
        chunk_size: int = 1000,
        overlap: int = 150,
        embedding_batch_size: int = 16,
    ) -> dict:
        if not chunks:
            raise ValueError("没有可用于构建索引的文本片段。")

        selected_backend = (backend or get_settings().retrieval_backend or "hybrid").lower()
        if selected_backend not in {"hybrid", "embedding", "tfidf"}:
            selected_backend = "hybrid"

        self.chunks = chunks
        texts = [chunk["text"] for chunk in chunks]
        build_tfidf = selected_backend in {"hybrid", "tfidf"}
        build_embedding = use_embedding and selected_backend in {"hybrid", "embedding"}
        embedding_warning = ""

        if build_tfidf:
            self.tfidf_vectorizer = TfidfVectorizer(
                analyzer="char_wb",
                ngram_range=(2, 4),
                max_features=200_000,
            )
            self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)

        if build_embedding:
            vectors = embed_texts(texts, batch_size=embedding_batch_size)
            if vectors is not None and vectors.size > 0 and len(vectors) == len(chunks):
                self.embedding_matrix = normalize(vectors, norm="l2")
            else:
                self.embedding_matrix = None
                embedding_warning = "Embedding 构建失败，已自动保留可用的 TF-IDF 索引。"

        if selected_backend == "embedding" and not self.has_embedding:
            if not self.has_tfidf:
                self.tfidf_vectorizer = TfidfVectorizer(
                    analyzer="char_wb",
                    ngram_range=(2, 4),
                    max_features=200_000,
                )
                self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)
            embedding_warning = "Embedding 构建失败，已 fallback 到 TF-IDF。"

        embedding_config = get_embedding_config()
        self.metadata = {
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "pdf_files": pdf_files or sorted({chunk.get("source_file", "") for chunk in chunks if chunk.get("source_file")}),
            "chunk_count": len(chunks),
            "chunk_size": chunk_size,
            "overlap": overlap,
            "retrieval_backend": selected_backend,
            "embedding_model": embedding_config["model"],
            "has_embedding": self.has_embedding,
            "has_tfidf": self.has_tfidf,
            "embedding_warning": embedding_warning,
        }
        return self.metadata

    def save_index(self, index_file: Path | None = None) -> None:
        target = index_file or self.index_file
        if not self.is_ready:
            raise ValueError("索引尚未构建，无法保存。")
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as file:
            pickle.dump(
                {
                    "chunks": self.chunks,
                    "tfidf_vectorizer": self.tfidf_vectorizer,
                    "tfidf_matrix": self.tfidf_matrix,
                    "embedding_matrix": self.embedding_matrix,
                    "metadata": self.metadata,
                },
                file,
            )

    @classmethod
    def load_index(cls, index_file: Path | None = None) -> "VectorStore":
        target = index_file or get_settings().index_file
        if not target.exists():
            raise FileNotFoundError(f"未发现索引文件：{target}")
        with target.open("rb") as file:
            payload = pickle.load(file)

        store = cls(index_file=target)
        store.chunks = payload.get("chunks", [])
        store.tfidf_vectorizer = payload.get("tfidf_vectorizer")
        if store.tfidf_vectorizer is None:
            store.tfidf_vectorizer = payload.get("vectorizer")
        store.tfidf_matrix = payload.get("tfidf_matrix")
        if store.tfidf_matrix is None:
            store.tfidf_matrix = payload.get("matrix")
        store.embedding_matrix = payload.get("embedding_matrix")
        store.metadata = payload.get("metadata", {})
        if not store.metadata:
            store.metadata = {
                "created_at": payload.get("built_at"),
                "chunk_count": len(store.chunks),
                "has_embedding": store.has_embedding,
                "has_tfidf": store.has_tfidf,
                "retrieval_backend": "tfidf",
                "embedding_model": "",
                "pdf_files": sorted({chunk.get("source_file", "") for chunk in store.chunks if chunk.get("source_file")}),
            }
        return store

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        return self.search_tfidf(query, top_k=top_k)

    def search_tfidf(self, query: str, top_k: int = 5, match_type: str = "tfidf") -> list[dict]:
        if not self.has_tfidf or not query.strip():
            return []
        limit = max(1, min(int(top_k), 50))
        query_vector = self.tfidf_vectorizer.transform([query])  # type: ignore[union-attr]
        scores = cosine_similarity(query_vector, self.tfidf_matrix).flatten()
        ranked_indices = scores.argsort()[::-1][:limit]
        return [self._result_from_index(int(idx), float(scores[int(idx)]), match_type) for idx in ranked_indices]

    def search_embedding(self, query: str, top_k: int = 5, match_type: str = "embedding") -> list[dict]:
        if not self.has_embedding or not query.strip():
            return []
        query_vector = embed_query(query)
        if query_vector is None or query_vector.size == 0:
            return []
        query_vector = normalize(query_vector.reshape(1, -1), norm="l2")
        scores = cosine_similarity(query_vector, self.embedding_matrix).flatten()
        limit = max(1, min(int(top_k), 50))
        ranked_indices = scores.argsort()[::-1][:limit]
        return [self._result_from_index(int(idx), float(scores[int(idx)]), match_type) for idx in ranked_indices]

    def search_hybrid(
        self,
        original_query: str,
        expanded_query: str = "",
        keywords: list[str] | None = None,
        top_k: int = 5,
    ) -> list[dict]:
        if not self.is_ready:
            return []

        keywords = keywords or []
        expanded_query = expanded_query or original_query
        keyword_text = " ".join(keywords)
        tfidf_full_query = " ".join(part for part in [original_query, expanded_query, keyword_text] if part.strip())

        candidates: list[dict] = []
        candidate_k = max(int(top_k) * 3, 10)

        candidates.extend(self.search_embedding(original_query, candidate_k, "embedding_original"))
        if expanded_query.strip() and expanded_query.strip() != original_query.strip():
            candidates.extend(self.search_embedding(expanded_query, candidate_k, "embedding_expanded"))
        candidates.extend(self.search_tfidf(original_query, candidate_k, "tfidf_original"))
        if expanded_query.strip() and expanded_query.strip() != original_query.strip():
            candidates.extend(self.search_tfidf(expanded_query, candidate_k, "tfidf_expanded"))
        if keyword_text.strip():
            candidates.extend(self.search_tfidf(tfidf_full_query, candidate_k, "tfidf_keywords"))

        merged: dict[tuple[str, int, str], dict] = {}
        weights = {
            "embedding_original": 1.0,
            "embedding_expanded": 0.95,
            "tfidf_original": 0.9,
            "tfidf_expanded": 0.85,
            "tfidf_keywords": 0.8,
        }
        for item in candidates:
            key = (item.get("source_file", ""), int(item.get("page", 0)), item.get("chunk_id", ""))
            weighted_score = float(item.get("score", 0.0)) * weights.get(item.get("match_type", ""), 0.75)
            if key not in merged:
                merged[key] = dict(item)
                merged[key]["combined_score"] = weighted_score
                merged[key]["match_types"] = [item.get("match_type", "unknown")]
            else:
                merged[key]["combined_score"] += weighted_score
                merged[key]["score"] = max(float(merged[key].get("score", 0.0)), float(item.get("score", 0.0)))
                match = item.get("match_type", "unknown")
                if match not in merged[key]["match_types"]:
                    merged[key]["match_types"].append(match)

        results = sorted(merged.values(), key=lambda item: item.get("combined_score", 0.0), reverse=True)
        final_results = results[: max(1, min(int(top_k), 10))]
        for rank, item in enumerate(final_results, start=1):
            item["rank"] = rank
            item["match_type"] = ", ".join(item.get("match_types", []))
            item["score"] = float(item.get("combined_score", item.get("score", 0.0)))
        return final_results

    def _result_from_index(self, idx: int, score: float, match_type: str) -> dict:
        chunk = dict(self.chunks[idx])
        chunk["score"] = score
        chunk["match_type"] = match_type
        return chunk


def get_saved_index_metadata(index_file: Path | None = None) -> dict:
    target = index_file or get_settings().index_file
    if not target.exists():
        return {
            "exists": False,
            "chunk_count": 0,
            "built_at": None,
            "has_embedding": False,
            "has_tfidf": False,
            "embedding_model": "",
            "retrieval_backend": "",
            "pdf_files": [],
            "message": "索引未构建",
        }
    store = VectorStore.load_index(target)
    metadata = dict(store.metadata)
    return {
        "exists": True,
        "chunk_count": len(store.chunks),
        "built_at": metadata.get("created_at"),
        "has_embedding": store.has_embedding,
        "has_tfidf": store.has_tfidf,
        "embedding_model": metadata.get("embedding_model", ""),
        "retrieval_backend": metadata.get("retrieval_backend", ""),
        "pdf_files": metadata.get("pdf_files", []),
        "message": "索引已构建",
    }
