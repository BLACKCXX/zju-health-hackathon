from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DEFAULT_MODELSCOPE_BASE_URL = "https://api-inference.modelscope.cn/v1/"
DEFAULT_MODELSCOPE_MODEL = "Qwen/Qwen3-235B-A22B-Instruct-2507"
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"
FALLBACK_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


@dataclass(frozen=True)
class Settings:
    base_dir: Path
    openai_api_key: str
    openai_base_url: str
    model_name: str
    retrieval_backend: str
    textbook_dir: Path
    index_dir: Path
    index_file: Path
    outputs_dir: Path
    upload_dir: Path
    embedding_model: str
    graph_model: str
    chunk_size: int
    chunk_overlap: int
    rag_top_k: int
    graph_top_k_per_book: int
    graph_global_top_k: int


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _api_key(name: str) -> str:
    value = _env(name)
    placeholders = {
        "your_modelscope_sdk_token_here",
        "your_modelscope_token_here",
        "your_api_key_here",
    }
    if value.lower() in placeholders:
        return ""
    return value


def _path_from_env(name: str, default: Path) -> Path:
    value = _env(name)
    if not value:
        return default.resolve()
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = BASE_DIR / path
    return path.resolve()


def get_llm_config(role: str = "default") -> dict[str, str]:
    normalized_role = (role or "default").strip().lower()
    if normalized_role not in {"default", "router", "answer", "summary", "graph"}:
        normalized_role = "default"

    default_api_key = _api_key("DEFAULT_API_KEY") or _api_key("OPENAI_API_KEY")
    default_base_url = _env("DEFAULT_BASE_URL") or _env("OPENAI_BASE_URL") or DEFAULT_MODELSCOPE_BASE_URL
    default_model = _env("DEFAULT_MODEL") or _env("MODEL_NAME") or DEFAULT_MODELSCOPE_MODEL

    if normalized_role == "default":
        return {"api_key": default_api_key, "base_url": default_base_url, "model": default_model}

    prefix = normalized_role.upper()
    return {
        "api_key": _api_key(f"{prefix}_API_KEY") or default_api_key,
        "base_url": _env(f"{prefix}_BASE_URL") or default_base_url,
        "model": _env(f"{prefix}_MODEL") or default_model,
    }


def get_embedding_config() -> dict[str, str]:
    default_config = get_llm_config("default")
    return {
        "api_key": _api_key("EMBEDDING_API_KEY") or default_config["api_key"],
        "base_url": _env("EMBEDDING_BASE_URL") or default_config["base_url"],
        "model": _env("EMBEDDING_MODEL") or DEFAULT_EMBEDDING_MODEL,
    }


def _int_env(name: str, default: int) -> int:
    try:
        return int(_env(name, str(default)))
    except ValueError:
        return default


def get_settings() -> Settings:
    default_llm = get_llm_config("default")
    index_dir = _path_from_env("INDEX_DIR", BASE_DIR / "indexes")
    outputs_dir = _path_from_env("OUTPUT_DIR", _path_from_env("OUTPUTS_DIR", BASE_DIR / "outputs"))
    return Settings(
        base_dir=BASE_DIR,
        openai_api_key=default_llm["api_key"],
        openai_base_url=default_llm["base_url"],
        model_name=default_llm["model"],
        retrieval_backend=(_env("RETRIEVAL_BACKEND", "hybrid") or "hybrid").lower(),
        textbook_dir=_path_from_env("TEXTBOOK_DIR", BASE_DIR / "textbooks"),
        index_dir=index_dir,
        index_file=index_dir / "healthpdf_index.pkl",
        outputs_dir=outputs_dir,
        upload_dir=_path_from_env("UPLOAD_DIR", BASE_DIR / "uploads"),
        embedding_model=_env("EMBEDDING_MODEL") or DEFAULT_EMBEDDING_MODEL,
        graph_model=_env("GRAPH_MODEL") or _env("ANSWER_MODEL") or default_llm["model"],
        chunk_size=_int_env("CHUNK_SIZE", 700),
        chunk_overlap=_int_env("CHUNK_OVERLAP", 80),
        rag_top_k=_int_env("RAG_TOP_K", 8),
        graph_top_k_per_book=_int_env("GRAPH_TOP_K_PER_BOOK", 5),
        graph_global_top_k=_int_env("GRAPH_GLOBAL_TOP_K", 30),
    )


def has_api_key(role: str = "default") -> bool:
    return bool(get_llm_config(role)["api_key"])


def list_pdf_files(pdf_dir: Path | None = None) -> list[Path]:
    directory = pdf_dir or get_settings().textbook_dir
    if not directory.exists():
        return []
    return sorted(directory.rglob("*.pdf"))
