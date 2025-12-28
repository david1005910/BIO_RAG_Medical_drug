"""Cohere API 클라이언트 - Reranking 서비스"""
import logging
from typing import Dict, List, Optional

import cohere

from app.core.config import settings

logger = logging.getLogger(__name__)


class CohereReranker:
    """Cohere Rerank API 클라이언트"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.COHERE_API_KEY
        self.model = settings.RERANK_MODEL
        self.enabled = bool(self.api_key) and settings.ENABLE_RERANKING

        if self.enabled:
            self.client = cohere.ClientV2(api_key=self.api_key)
            logger.info(f"Cohere Reranker initialized with model: {self.model}")
        else:
            self.client = None
            logger.warning("Cohere Reranker disabled: No API key provided or disabled in settings")

    async def rerank(
        self,
        query: str,
        documents: List[Dict],
        top_n: Optional[int] = None,
        document_key: str = "document",
    ) -> List[Dict]:
        """문서 재순위 지정

        Args:
            query: 사용자 쿼리
            documents: 재순위할 문서 목록 (각 문서는 dict)
            top_n: 반환할 상위 문서 수 (기본값: settings.RERANK_TOP_N)
            document_key: 문서 텍스트가 있는 키

        Returns:
            재순위된 문서 목록 (relevance_score 포함)
        """
        if not self.enabled or not documents:
            logger.debug("Reranking skipped: disabled or no documents")
            return documents

        top_n = top_n or settings.RERANK_TOP_N

        # 문서 텍스트 추출 - 효능 정보를 우선으로 상세하게 구성
        doc_texts = []
        for doc in documents:
            # 의약품 정보일 경우 효능 중심으로 상세 텍스트 생성
            if doc.get("efficacy") or doc.get("item_name"):
                efficacy = doc.get("efficacy", "")
                # 효능 정보를 최우선으로 하여 검색어와의 관련성 향상
                text = f"{efficacy}. 제품명: {doc.get('item_name', '')}."
                if doc.get("caution_info"):
                    # 주의사항에서 적용증 관련 정보 추출
                    text += f" 적용: {doc.get('caution_info', '')[:200]}"
            elif document_key in doc:
                text = doc[document_key]
            else:
                # 기타 문서
                parts = []
                for key in ["name", "symptoms", "causes", "treatment", "efficacy"]:
                    if doc.get(key):
                        parts.append(str(doc[key]))
                text = " ".join(parts) if parts else str(doc)
            doc_texts.append(text)

        try:
            logger.info(f"Reranking {len(documents)} documents for query: {query[:50]}...")

            response = self.client.rerank(
                model=self.model,
                query=query,
                documents=doc_texts,
                top_n=min(top_n, len(documents)),
            )

            # 재순위 결과 적용
            reranked_docs = []
            for result in response.results:
                doc = documents[result.index].copy()
                doc["relevance_score"] = result.relevance_score
                doc["original_rank"] = result.index
                reranked_docs.append(doc)

            logger.info(f"Reranking complete: {len(reranked_docs)} results")
            return reranked_docs

        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            # 실패 시 원본 문서 반환
            return documents[:top_n] if top_n else documents

    def is_enabled(self) -> bool:
        """Reranker 활성화 여부"""
        return self.enabled


# 싱글톤 인스턴스
_reranker: Optional[CohereReranker] = None


def get_reranker() -> CohereReranker:
    """Cohere Reranker 싱글톤 반환"""
    global _reranker
    if _reranker is None:
        _reranker = CohereReranker()
    return _reranker
