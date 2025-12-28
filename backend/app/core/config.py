"""Application configuration settings"""
from functools import lru_cache
from typing import List, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # API Keys
    DATA_GO_KR_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    COHERE_API_KEY: str = ""

    # Database (SQLite for local development, PostgreSQL for production)
    DATABASE_URL: str = "sqlite+aiosqlite:///./medical_rag.db"

    # Redis (Optional)
    REDIS_URL: str = "redis://localhost:6379"

    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    API_KEY: str = ""  # Optional API key for admin endpoints

    # CORS
    ALLOWED_ORIGINS: Union[str, List[str]] = ["http://localhost:3000", "http://localhost:5173"]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # OpenAI Settings
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536
    LLM_MODEL: str = "gpt-4o-mini"

    # Search Settings
    DEFAULT_TOP_K: int = 5
    MAX_TOP_K: int = 20

    # Hybrid Search Settings (Dense + Sparse)
    ENABLE_HYBRID_SEARCH: bool = True
    DENSE_WEIGHT: float = 0.7  # Vector search weight
    SPARSE_WEIGHT: float = 0.3  # BM25 search weight

    # Reranking Settings
    ENABLE_RERANKING: bool = True
    RERANK_MODEL: str = "rerank-multilingual-v3.0"
    RERANK_TOP_N: int = 5  # Number of results after reranking

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
