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

    # Qdrant Settings
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION_NAME: str = "medical_drugs"
    ENABLE_QDRANT: bool = True

    # BGE-M3 Sparse Embedding Settings (SPLADE 대체)
    # BGE-M3는 100+ 언어 지원 (한국어 포함)
    SPLADE_MODEL: str = "BAAI/bge-m3"  # 실제로는 BGE-M3 사용
    SPLADE_MAX_SCORE: float = 10.0  # BGE-M3 점수 정규화 기준 (SPLADE보다 낮음)

    # Search Settings
    DEFAULT_TOP_K: int = 5
    MAX_TOP_K: int = 20

    # Hybrid Search Settings (Dense + Sparse)
    # BGE-M3는 한국어를 정상 지원하므로 균형 잡힌 가중치 사용
    # Hybrid Score = Dense * 0.7 + Sparse * 0.3
    ENABLE_HYBRID_SEARCH: bool = True
    DENSE_WEIGHT: float = 0.7  # Vector search weight (semantic understanding)
    SPARSE_WEIGHT: float = 0.3  # BGE-M3 sparse weight (lexical matching)

    # Reranking Settings
    ENABLE_RERANKING: bool = True
    RERANK_MODEL: str = "rerank-multilingual-v3.0"
    RERANK_TOP_N: int = 5  # Number of results after reranking

    # Neo4j Graph Database Settings
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = ""
    NEO4J_DATABASE: str = "neo4j"
    ENABLE_NEO4J: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
