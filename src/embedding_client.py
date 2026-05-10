from __future__ import annotations

import os
import time
from pathlib import Path

import numpy as np

# Try to import sentence-transformers for local embedding
try:
    from sentence_transformers import SentenceTransformer
    _LOCAL_EMBEDDING_AVAILABLE = True
except ImportError:
    _LOCAL_EMBEDDING_AVAILABLE = False

from .config import get_embedding_config, get_settings


_LOCAL_MODELS = {
    "BAAI/bge-small-zh-v1.5": "BAAI/bge-small-zh-v1.5",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2": "paraphrase-multilingual-MiniLM-L12-v2",
}


def _get_local_model(model_name: str):
    """Get local sentence-transformers model, with fallback."""
    if not _LOCAL_EMBEDDING_AVAILABLE:
        return None

    cache_folder = Path.home() / ".cache" / "hf_embeddings"
    mapped_name = _LOCAL_MODELS.get(model_name, model_name)

    try:
        return SentenceTransformer(mapped_name, cache_folder=str(cache_folder))
    except Exception:
        # Try fallback model
        try:
            fallback = "paraphrase-multilingual-MiniLM-L12-v2"
            return SentenceTransformer(fallback, cache_folder=str(cache_folder))
        except Exception:
            return None


def embed_texts_local(texts: list[str], model_name: str, batch_size: int = 32) -> np.ndarray | None:
    """Embed texts using local sentence-transformers model."""
    model = _get_local_model(model_name)
    if model is None:
        return None

    try:
        embeddings = model.encode(texts, batch_size=batch_size, show_progress_bar=False, normalize_embeddings=True)
        return np.array(embeddings, dtype=np.float32)
    except Exception:
        return None


def embed_query_local(query: str, model_name: str) -> np.ndarray | None:
    """Embed a single query using local model."""
    result = embed_texts_local([query], model_name, batch_size=1)
    if result is None or result.size == 0:
        return None
    return result[0]


def embed_texts(
    texts: list[str],
    batch_size: int = 16,
    max_retries: int = 2,
) -> np.ndarray | None:
    """Embed texts with local model first, then API fallback."""
    settings = get_settings()
    embedding_model = settings.embedding_model or "BAAI/bge-small-zh-v1.5"

    # Try local model first
    local_result = embed_texts_local(texts, embedding_model, batch_size=batch_size)
    if local_result is not None and local_result.size > 0 and len(local_result) == len(texts):
        return local_result

    # Fallback to API
    config = get_embedding_config()
    api_key = config["api_key"]
    base_url = config["base_url"]
    model = config["model"]
    if not api_key or not model:
        return None
    if not texts:
        return np.empty((0, 0), dtype=np.float32)

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url)
        vectors: list[list[float]] = []
        batch_size = max(1, min(int(batch_size), 64))

        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            last_error: Exception | None = None
            for attempt in range(max_retries + 1):
                try:
                    response = client.embeddings.create(
                        model=model,
                        input=batch,
                        encoding_format="float",
                    )
                    vectors.extend([item.embedding for item in response.data])
                    last_error = None
                    break
                except Exception as exc:
                    last_error = exc
                    if attempt < max_retries:
                        time.sleep(1.5 * (attempt + 1))
            if last_error is not None:
                return None

        return np.array(vectors, dtype=np.float32)
    except Exception:
        return None


def embed_query(text: str) -> np.ndarray | None:
    """Embed a single query with local model first."""
    settings = get_settings()
    embedding_model = settings.embedding_model or "BAAI/bge-small-zh-v1.5"

    # Try local first
    local_vec = embed_query_local(text, embedding_model)
    if local_vec is not None:
        return local_vec

    # Fallback to API
    vectors = embed_texts([text], batch_size=1, max_retries=1)
    if vectors is None or vectors.size == 0:
        return None
    return vectors[0]