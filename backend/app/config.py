import os
from functools import lru_cache
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

_env_file = Path(__file__).parent.parent / ".env"
load_dotenv(_env_file, override=True)

_initialized = False


def _init_langsmith():
    global _initialized
    if _initialized:
        return
    _initialized = True
    if os.getenv("LANGSMITH_API_KEY"):
        os.environ.setdefault("LANGCHAIN_TRACING_V2", os.getenv("LANGCHAIN_TRACING_V2", "true"))
        os.environ.setdefault("LANGCHAIN_API_KEY", os.getenv("LANGSMITH_API_KEY"))
        os.environ.setdefault("LANGCHAIN_PROJECT", os.getenv("LANGCHAIN_PROJECT", "hybridrag"))
        os.environ.setdefault("LANGCHAIN_ENDPOINT", os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com"))


_init_langsmith()


class Settings(BaseSettings):
    app_name: str = "Hybrid RAG API"
    debug: bool = False

    database_url: str

    clerk_jwks_url: str = ""
    clerk_secret_key: str = ""
    admin_email: str = ""

    chroma_api_key: str = ""
    chroma_tenant: str = ""
    chroma_database: str = "raglocal"
    chroma_collection: str = "raglocal_vectors"

    b2_key_id: str = ""
    b2_application_key: str = ""
    b2_bucket_name: str = "raglocal"
    b2_bucket_endpoint: str = "https://s3.us-east-005.backblazeb2.com"
    b2_region: str = "us-east-005"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_text_embedding_model: str = "text-embedding-3-large"

    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    max_upload_mb: int = 100
    max_files_per_upload: int = 5

    chunk_size: int = 1000
    chunk_overlap: int = 200
    min_chunk_length: int = 50
    semantic_chunking_enabled: bool = True
    semantic_similarity_threshold: float = 0.65
    max_chunk_size: int = 1500
    min_semantic_chunk_length: int = 100
    chunk_validation_min_alpha_ratio: float = 0.3
    chunk_validation_min_words: int = 5

    top_k_chunks: int = 10
    rerank_top_n: int = 5
    max_completion_tokens: int = 4000
    rag_temperature: float = 0.7
    max_history_messages: int = 20

    hyde_enabled: bool = True
    hyde_model: str = "gpt-4o"
    hyde_temperature: float = 0.3
    hyde_max_tokens: int = 1024

    cohere_api_key: str = ""

    langsmith_api_key: str = ""
    langchain_tracing_v2: bool = True
    langchain_project: str = "hybridrag"
    langchain_endpoint: str = "https://api.smith.langchain.com"

    neo4j_uri: str = ""
    neo4j_user: str = ""
    neo4j_password: str = ""

    model_config = {
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()
