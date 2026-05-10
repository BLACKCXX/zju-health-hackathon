from __future__ import annotations

import time

import numpy as np
from openai import OpenAI

from .config import get_embedding_config


def embed_texts(
    texts: list[str],
    batch_size: int = 16,
    max_retries: int = 2,
) -> np.ndarray | None:
    config = get_embedding_config()
    api_key = config["api_key"]
    base_url = config["base_url"]
    model = config["model"]
    if not api_key or not model:
        return None
    if not texts:
        return np.empty((0, 0), dtype=np.float32)

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


def embed_query(text: str) -> np.ndarray | None:
    vectors = embed_texts([text], batch_size=1, max_retries=1)
    if vectors is None or vectors.size == 0:
        return None
    return vectors[0]
