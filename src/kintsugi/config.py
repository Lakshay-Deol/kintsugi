"""Central configuration — all values from environment variables only."""
from __future__ import annotations
import os
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()


def _required(key: str) -> str:
    val = os.environ.get(key, "")
    if not val:
        raise RuntimeError(f"Required environment variable {key!r} is not set.")
    return val


def _opt(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def _int(key: str, default: int) -> int:
    return int(os.environ.get(key, default))


def _float(key: str, default: float) -> float:
    return float(os.environ.get(key, default))


def _bool(key: str, default: bool = False) -> bool:
    val = os.environ.get(key, "").strip().lower()
    if val in ("1", "true", "yes"):
        return True
    if val in ("0", "false", "no"):
        return False
    return default


@lru_cache(maxsize=1)
def get_config() -> "Config":
    return Config()


class Config:
    # MongoDB
    mongodb_uri: str
    mongodb_db: str
    manuals_collection: str
    chunks_collection: str
    error_codes_collection: str
    fix_outcomes_collection: str
    ingest_jobs_collection: str
    atlas_vector_index: str
    atlas_search_index: str

    # LLM
    llm_api_key: str
    llm_base_url: str
    llm_model: str
    llm_timeout_seconds: int
    llm_max_attempts: int
    llm_retry_base_seconds: float
    llm_max_tokens: int

    # Embeddings
    embedding_model: str
    embedding_dims: int
    skip_embedder_warmup: bool

    # Retrieval gates
    min_vector_score: float
    min_bm25_score: float
    rrf_k: int
    vector_top_k: int
    bm25_top_k: int
    final_top_k: int

    # Rate limiting
    rate_limit_per_ip: int
    rate_limit_global: int
    rate_limit_window_seconds: int

    # App
    api_host: str
    api_port: int
    app_env: str
    demo_mode: bool

    def __init__(self) -> None:
        self.mongodb_uri = _opt("MONGODB_URI", "mongodb://localhost:27017")
        self.mongodb_db = _opt("MONGODB_DB", "kintsugi")
        self.manuals_collection = _opt("MONGODB_MANUALS_COLLECTION", "manuals")
        self.chunks_collection = _opt("MONGODB_CHUNKS_COLLECTION", "chunks")
        self.error_codes_collection = _opt("MONGODB_ERROR_CODES_COLLECTION", "error_codes")
        self.fix_outcomes_collection = _opt("MONGODB_FIX_OUTCOMES_COLLECTION", "fix_outcomes")
        self.ingest_jobs_collection = _opt("MONGODB_INGEST_JOBS_COLLECTION", "ingest_jobs")
        self.atlas_vector_index = _opt("ATLAS_VECTOR_INDEX", "vector_index")
        self.atlas_search_index = _opt("ATLAS_SEARCH_INDEX", "bm25_index")

        self.llm_api_key = _opt("LLM_API_KEY", "demo-placeholder-key")
        self.llm_base_url = _opt(
            "LLM_BASE_URL",
            "https://generativelanguage.googleapis.com/v1beta/openai/",
        )
        self.llm_model = _opt("LLM_MODEL", "gemma-3-27b-it")
        self.llm_timeout_seconds = _int("LLM_TIMEOUT_SECONDS", 60)
        self.llm_max_attempts = _int("LLM_MAX_ATTEMPTS", 3)
        self.llm_retry_base_seconds = _float("LLM_RETRY_BASE_SECONDS", 1.0)
        self.llm_max_tokens = _int("LLM_MAX_TOKENS", 2048)

        self.embedding_model = _opt("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
        self.embedding_dims = _int("EMBEDDING_DIMS", 384)
        self.skip_embedder_warmup = _bool("SKIP_EMBEDDER_WARMUP", False)

        self.min_vector_score = _float("MIN_VECTOR_SCORE", 0.70)
        self.min_bm25_score = _float("MIN_BM25_SCORE", 5.0)
        self.rrf_k = _int("RRF_K", 60)
        self.vector_top_k = _int("VECTOR_TOP_K", 10)
        self.bm25_top_k = _int("BM25_TOP_K", 10)
        self.final_top_k = _int("FINAL_TOP_K", 5)

        self.rate_limit_per_ip = _int("RATE_LIMIT_PER_IP", 5)
        self.rate_limit_global = _int("RATE_LIMIT_GLOBAL", 20)
        self.rate_limit_window_seconds = _int("RATE_LIMIT_WINDOW_SECONDS", 60)

        self.api_host = _opt("API_HOST", "0.0.0.0")
        self.api_port = _int("API_PORT", 8080)
        self.app_env = _opt("APP_ENV", "development")
        self.demo_mode = _bool("DEMO_MODE", True)

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"
