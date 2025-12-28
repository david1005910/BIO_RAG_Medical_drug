"""임베딩 서비스 - OpenAI 임베딩 래퍼"""
import logging
from typing import List, Optional

from app.external.openai_client import OpenAIClient
from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """OpenAI 임베딩 서비스 래퍼"""

    def __init__(self, client: Optional[OpenAIClient] = None):
        self.client = client or OpenAIClient()
        self.dimensions = settings.EMBEDDING_DIMENSIONS

    async def embed_text(self, text: str) -> List[float]:
        """단일 텍스트를 임베딩 벡터로 변환

        Args:
            text: 임베딩할 텍스트

        Returns:
            임베딩 벡터 (1536 차원)
        """
        return await self.client.embed_text(text)

    async def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 100,
    ) -> List[List[float]]:
        """텍스트 배치를 임베딩 벡터로 변환

        Args:
            texts: 임베딩할 텍스트 리스트
            batch_size: 배치 크기

        Returns:
            임베딩 벡터 리스트
        """
        return await self.client.embed_batch(texts, batch_size)

    async def embed_drug_documents(
        self,
        documents: List[str],
    ) -> List[List[float]]:
        """의약품 문서 배치 임베딩

        Args:
            documents: RAG용 의약품 문서 리스트

        Returns:
            임베딩 벡터 리스트
        """
        logger.info(f"📊 {len(documents)}개 의약품 문서 임베딩 시작...")
        embeddings = await self.embed_batch(documents)
        logger.info(f"✅ 임베딩 완료: {len(embeddings)}개")
        return embeddings


# 싱글톤 인스턴스
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """임베딩 서비스 싱글톤 반환"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
