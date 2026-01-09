"""LLM 서비스 - 응답 생성"""
import logging
from typing import Dict, List, Optional

from app.external.openai_client import OpenAIClient

logger = logging.getLogger(__name__)


class LLMService:
    """OpenAI LLM 서비스 래퍼"""

    def __init__(self, client: Optional[OpenAIClient] = None):
        self.client = client or OpenAIClient()

    async def generate_response(
        self,
        query: str,
        context: str,
        temperature: float = 0.3,
    ) -> str:
        """RAG 기반 응답 생성

        Args:
            query: 사용자 질문
            context: 검색된 의약품 정보 컨텍스트
            temperature: 생성 온도

        Returns:
            생성된 응답 텍스트
        """
        return await self.client.generate_response(
            query=query,
            context=context,
            temperature=temperature,
        )

    async def generate_integrated_response(
        self,
        query: str,
        context: str,
        temperature: float = 0.3,
    ) -> str:
        """질병 + 의약품 통합 RAG 응답 생성

        Args:
            query: 사용자 질문
            context: 검색된 질병 + 의약품 정보 컨텍스트
            temperature: 생성 온도

        Returns:
            생성된 응답 텍스트
        """
        return await self.client.generate_integrated_response(
            query=query,
            context=context,
            temperature=temperature,
        )

    def format_context(self, results: List[Dict]) -> str:
        """검색 결과를 LLM 컨텍스트로 포맷팅

        Args:
            results: 벡터 검색 결과

        Returns:
            포맷팅된 컨텍스트 문자열
        """
        return self.client.format_context(results)

    def format_integrated_context(
        self,
        drug_results: List[Dict],
        disease_results: List[Dict],
    ) -> str:
        """질병 + 의약품 통합 컨텍스트 포맷팅

        Args:
            drug_results: 의약품 검색 결과
            disease_results: 질병 검색 결과

        Returns:
            포맷팅된 컨텍스트 문자열
        """
        return self.client.format_integrated_context(drug_results, disease_results)


# 싱글톤 인스턴스
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """LLM 서비스 싱글톤 반환"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
