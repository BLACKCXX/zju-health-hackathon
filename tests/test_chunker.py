import pytest

from src.chunker import chunk_text


def test_chunk_text_basic():
    text = "细胞水肿" * 120

    chunks = chunk_text(text, chunk_size=100, overlap=20)

    assert len(chunks) > 1
    assert all(len(chunk) <= 100 for chunk in chunks)
    assert "细胞水肿" in chunks[0]


def test_chunk_empty_text():
    assert chunk_text("") == []
    assert chunk_text("   \n\n  ") == []


def test_chunk_overlap_validation():
    with pytest.raises(ValueError, match="chunk_size must be greater than overlap"):
        chunk_text("abc" * 100, chunk_size=50, overlap=50)
