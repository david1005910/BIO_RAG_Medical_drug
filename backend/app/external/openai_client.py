"""OpenAI API 클라이언트 (임베딩 + LLM)"""
import logging
from typing import List, Optional

from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


class OpenAIClient:
    """OpenAI API 통합 클라이언트"""

    def __init__(self, api_key: Optional[str] = None):
        self.client = AsyncOpenAI(api_key=api_key or settings.OPENAI_API_KEY)
        self.embedding_model = settings.EMBEDDING_MODEL
        self.embedding_dimensions = settings.EMBEDDING_DIMENSIONS
        self.llm_model = settings.LLM_MODEL

    # ==================== Embedding Methods ====================

    async def embed_text(self, text: str) -> List[float]:
        """단일 텍스트 임베딩

        Args:
            text: 임베딩할 텍스트

        Returns:
            1536 차원 벡터
        """
        try:
            response = await self.client.embeddings.create(
                model=self.embedding_model,
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"임베딩 생성 실패: {e}")
            raise

    async def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 100,
    ) -> List[List[float]]:
        """배치 임베딩 (비용 효율적)

        Args:
            texts: 임베딩할 텍스트 리스트
            batch_size: 배치 크기 (최대 2048)

        Returns:
            임베딩 벡터 리스트
        """
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            logger.info(f"임베딩 배치 {i // batch_size + 1}/{(len(texts) - 1) // batch_size + 1}")

            try:
                response = await self.client.embeddings.create(
                    model=self.embedding_model,
                    input=batch,
                )

                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)

            except Exception as e:
                logger.error(f"배치 임베딩 실패: {e}")
                raise

        return all_embeddings

    # ==================== LLM Methods ====================

    async def generate_response(
        self,
        query: str,
        context: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> str:
        """RAG 기반 응답 생성

        Args:
            query: 사용자 질문
            context: 검색된 컨텍스트 (의약품 정보)
            system_prompt: 시스템 프롬프트 (없으면 기본값 사용)
            temperature: 생성 온도 (0~1)
            max_tokens: 최대 토큰 수

        Returns:
            생성된 응답 텍스트
        """
        if system_prompt is None:
            system_prompt = self._get_default_system_prompt()

        user_prompt = f"""
사용자 질문: {query}

참고할 의약품 정보:
{context}

위 정보를 바탕으로 사용자의 증상에 적합한 의약품을 추천해주세요.
각 의약품의 효능, 사용법, 주의사항을 친절하게 설명해주세요.
"""

        try:
            response = await self.client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"LLM 응답 생성 실패: {e}")
            raise

    async def generate_chat_response(
        self,
        message: str,
        context: str,
        temperature: float = 0.5,
    ) -> str:
        """대화형 응답 생성

        Args:
            message: 사용자 메시지
            context: 검색된 컨텍스트

        Returns:
            생성된 응답
        """
        return await self.generate_response(
            query=message,
            context=context,
            temperature=temperature,
        )

    def _get_default_system_prompt(self) -> str:
        """기본 시스템 프롬프트"""
        return """당신은 의약품 전문 상담 AI입니다.
주어진 의약품 정보를 바탕으로 사용자의 증상에 적합한 의약품을 추천해주세요.

중요 지침:
1. 반드시 주어진 컨텍스트 내의 의약품만 추천하세요.
2. 각 의약품의 효능효과, 사용법, 주의사항을 명확히 설명하세요.
3. 심각한 증상인 경우 반드시 전문의 상담을 권유하세요.
4. 답변은 친절하고 이해하기 쉽게 작성하세요.
5. 절대로 진단이나 처방을 하지 마세요. 정보 제공만 하세요.

응답 형식:
- 추천 의약품을 명확히 구분해서 설명
- 각 의약품별 효능, 용법, 주의사항 포함
- 마지막에 면책 조항 포함

⚠️ 면책 조항: 이 정보는 참고용이며, 실제 복약은 의사/약사와 상담하세요."""

    def format_context(self, results: List[dict]) -> str:
        """검색 결과를 LLM 컨텍스트로 포맷팅

        Args:
            results: 검색 결과 리스트

        Returns:
            포맷팅된 컨텍스트 문자열
        """
        context_parts = []

        for i, result in enumerate(results, 1):
            # 관련성 점수 표시 (reranking 사용 시)
            relevance = result.get('relevance_score')
            score_text = f"관련성: {relevance:.2%}" if relevance else f"유사도: {result.get('similarity', 0):.2%}"

            part = f"""
[의약품 {i}] {result.get('item_name', '알 수 없음')}
- 제조사: {result.get('entp_name', '알 수 없음')}
- 효능효과: {result.get('efficacy', '정보 없음')}
- 용법용량: {result.get('use_method', '정보 없음')}
- 주의사항: {result.get('caution_info', '정보 없음')}
- 부작용: {result.get('side_effects', '정보 없음')}
- {score_text}
"""
            context_parts.append(part)

        return "\n---\n".join(context_parts)

    def format_integrated_context(
        self,
        drug_results: List[dict],
        disease_results: List[dict],
    ) -> str:
        """질병 + 의약품 통합 컨텍스트 포맷팅

        Args:
            drug_results: 의약품 검색 결과
            disease_results: 질병 검색 결과

        Returns:
            포맷팅된 통합 컨텍스트 문자열
        """
        context_parts = []

        # 질병 정보 섹션
        if disease_results:
            context_parts.append("=== 관련 질병 정보 ===\n")
            for i, disease in enumerate(disease_results, 1):
                relevance = disease.get('relevance_score')
                score_text = f"관련성: {relevance:.2%}" if relevance else f"유사도: {disease.get('similarity', 0):.2%}"

                part = f"""
[질병 {i}] {disease.get('name', '알 수 없음')}
- 분류: {disease.get('category', '정보 없음')}
- 설명: {disease.get('description', '정보 없음')}
- 원인: {disease.get('causes', '정보 없음')}
- 증상: {disease.get('symptoms', '정보 없음')}
- 치료: {disease.get('treatment', '정보 없음')}
- 예방: {disease.get('prevention', '정보 없음')}
- 관련 의약품: {disease.get('related_drugs', '정보 없음')}
- {score_text}
"""
                context_parts.append(part)

        # 의약품 정보 섹션
        if drug_results:
            context_parts.append("\n=== 추천 의약품 정보 ===\n")
            for i, drug in enumerate(drug_results, 1):
                relevance = drug.get('relevance_score')
                score_text = f"관련성: {relevance:.2%}" if relevance else f"유사도: {drug.get('similarity', 0):.2%}"

                part = f"""
[의약품 {i}] {drug.get('item_name', '알 수 없음')}
- 제조사: {drug.get('entp_name', '알 수 없음')}
- 효능효과: {drug.get('efficacy', '정보 없음')}
- 용법용량: {drug.get('use_method', '정보 없음')}
- 주의사항: {drug.get('caution_info', '정보 없음')}
- 부작용: {drug.get('side_effects', '정보 없음')}
- {score_text}
"""
                context_parts.append(part)

        return "\n".join(context_parts)

    async def generate_integrated_response(
        self,
        query: str,
        context: str,
        temperature: float = 0.3,
        max_tokens: int = 2500,
    ) -> str:
        """질병 + 의약품 통합 RAG 응답 생성

        Args:
            query: 사용자 질문
            context: 검색된 질병 + 의약품 컨텍스트
            temperature: 생성 온도
            max_tokens: 최대 토큰 수

        Returns:
            생성된 응답 텍스트
        """
        system_prompt = self._get_integrated_system_prompt()

        user_prompt = f"""
사용자 질문: {query}

참고 정보:
{context}

위 정보를 바탕으로 다음을 포함하여 상세히 답변해주세요:
1. 관련 질병에 대한 설명 (원인, 증상)
2. 적합한 의약품 추천과 설명
3. 치료 및 예방 방법
4. 주의사항
"""

        try:
            response = await self.client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"통합 LLM 응답 생성 실패: {e}")
            raise

    def _get_integrated_system_prompt(self) -> str:
        """통합 응답용 시스템 프롬프트"""
        return """당신은 건강 정보와 의약품 전문 상담 AI입니다.
주어진 질병 정보와 의약품 정보를 바탕으로 사용자의 증상에 대해 상세히 설명해주세요.

중요 지침:
1. 먼저 사용자의 증상과 관련된 질병에 대해 설명하세요 (원인, 증상, 치료법).
2. 관련 질병 정보를 바탕으로 적합한 의약품을 추천하세요.
3. 각 의약품의 효능, 사용법, 주의사항을 명확히 설명하세요.
4. 예방법과 생활습관 개선 방법도 함께 안내하세요.
5. 심각한 증상인 경우 반드시 전문의 상담을 권유하세요.
6. 답변은 친절하고 이해하기 쉽게 작성하세요.
7. 절대로 진단이나 처방을 하지 마세요. 정보 제공만 하세요.

응답 형식:
## 관련 질병 정보
- 질병에 대한 설명

## 추천 의약품
- 각 의약품별 설명

## 치료 및 예방
- 치료 방법과 예방법

## 주의사항
- 중요한 주의사항

⚠️ 면책 조항: 이 정보는 참고용이며, 정확한 진단과 처방을 위해 반드시 의사/약사와 상담하세요."""
