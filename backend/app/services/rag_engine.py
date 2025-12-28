"""RAG 엔진 - 검색 + 생성 통합"""
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.embedding import get_embedding_service, EmbeddingService
from app.services.vector_db import VectorDBService
from app.services.disease_vector_db import DiseaseVectorDBService
from app.services.llm_service import get_llm_service, LLMService
from app.services.bm25_search import get_hybrid_service, HybridSearchService
from app.external.cohere_client import get_reranker, CohereReranker

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """검색 결과 데이터 클래스"""

    drug_id: str
    item_name: str
    entp_name: Optional[str]
    efficacy: Optional[str]
    use_method: Optional[str]
    caution_info: Optional[str]
    side_effects: Optional[str]
    similarity: float
    relevance_score: Optional[float] = None  # Cohere reranking score


@dataclass
class DiseaseResult:
    """질병 검색 결과 데이터 클래스"""

    disease_id: str
    name: str
    name_en: Optional[str]
    category: Optional[str]
    description: Optional[str]
    causes: Optional[str]
    symptoms: Optional[str]
    treatment: Optional[str]
    prevention: Optional[str]
    related_drugs: Optional[str]
    similarity: float
    relevance_score: Optional[float] = None


@dataclass
class RAGResponse:
    """RAG 응답 데이터 클래스"""

    results: List[SearchResult]
    disease_results: Optional[List[DiseaseResult]] = None
    ai_response: Optional[str] = None
    disclaimer: str = "※ 이 정보는 참고용입니다. 실제 복약은 의사/약사와 상담하세요."


class RAGEngine:
    """의약품 + 질병 정보 RAG 엔진

    검색(Retrieval) + 재순위(Reranking) + 생성(Generation)을 통합한 핵심 엔진
    Hybrid Search: Dense (Vector) + Sparse (BM25) 결합 지원
    """

    def __init__(
        self,
        session: AsyncSession,
        embedding_service: Optional[EmbeddingService] = None,
        llm_service: Optional[LLMService] = None,
        reranker: Optional[CohereReranker] = None,
        hybrid_service: Optional[HybridSearchService] = None,
    ):
        self.session = session
        self.vector_db = VectorDBService(session)
        self.disease_vector_db = DiseaseVectorDBService(session)
        self.embedding_service = embedding_service or get_embedding_service()
        self.llm_service = llm_service or get_llm_service()
        self.reranker = reranker or get_reranker()

        # Hybrid Search 설정
        self.enable_hybrid = settings.ENABLE_HYBRID_SEARCH
        if self.enable_hybrid:
            self.hybrid_service = hybrid_service or get_hybrid_service(
                session,
                dense_weight=settings.DENSE_WEIGHT,
                sparse_weight=settings.SPARSE_WEIGHT,
            )
        else:
            self.hybrid_service = None

    async def search(
        self,
        query: str,
        top_k: int = 5,
        use_reranking: bool = True,
        use_hybrid: bool = True,
    ) -> List[SearchResult]:
        """증상 기반 의약품 검색 (LLM 응답 없음)

        Args:
            query: 사용자 증상 설명
            top_k: 반환할 결과 수
            use_reranking: Cohere reranking 사용 여부
            use_hybrid: Hybrid Search (Dense + BM25) 사용 여부

        Returns:
            유사도/관련성 순으로 정렬된 검색 결과
        """
        logger.info(f"🔍 검색 쿼리: {query[:50]}...")

        # 1. 쿼리 임베딩
        query_embedding = await self.embedding_service.embed_text(query)

        # 2. 벡터 유사도 검색 (Dense Search)
        # reranking 또는 hybrid 사용시 더 많이 가져옴
        expand_factor = 5 if (use_reranking and self.reranker.is_enabled()) else 3
        initial_top_k = top_k * expand_factor
        dense_results = await self.vector_db.search_similar(query_embedding, initial_top_k)

        # 3. Hybrid Search (Dense + BM25 결합)
        if use_hybrid and self.enable_hybrid and self.hybrid_service:
            logger.info(f"🔀 Hybrid Search 적용 중... (Dense={len(dense_results)}개)")
            try:
                results = await self.hybrid_service.search(
                    query=query,
                    dense_results=dense_results,
                    top_k=initial_top_k,
                )
                logger.info(f"✅ Hybrid Search 완료: {len(results)}개 결과")
            except Exception as e:
                logger.warning(f"⚠️ Hybrid Search 실패, Dense만 사용: {e}")
                results = dense_results
        else:
            results = dense_results

        # 4. Cohere Reranking (활성화된 경우)
        if use_reranking and self.reranker.is_enabled() and results:
            logger.info(f"🔄 Cohere Reranking 적용 중... ({len(results)}개 문서)")
            results = await self.reranker.rerank(
                query=query,
                documents=results,
                top_n=top_k,
            )
            logger.info(f"✅ Reranking 완료: {len(results)}개 결과")
        else:
            # Reranking 없으면 top_k만큼만 반환
            results = results[:top_k]

        # 5. SearchResult로 변환
        search_results = [
            SearchResult(
                drug_id=r["drug_id"],
                item_name=r["item_name"],
                entp_name=r["entp_name"],
                efficacy=r["efficacy"],
                use_method=r["use_method"],
                caution_info=r["caution_info"],
                side_effects=r["side_effects"],
                similarity=r["similarity"],
                relevance_score=r.get("relevance_score"),
            )
            for r in results
        ]

        # 로그에 검색 방식 표시
        search_type = []
        if use_hybrid and self.enable_hybrid:
            search_type.append("Hybrid(Dense+BM25)")
        else:
            search_type.append("Dense")
        if use_reranking and self.reranker.is_enabled():
            search_type.append("Reranking")

        logger.info(f"✅ {len(search_results)}개 결과 반환 [{'+'.join(search_type)}]")
        return search_results

    async def search_diseases(
        self,
        query: str,
        top_k: int = 3,
        use_reranking: bool = True,
    ) -> List[DiseaseResult]:
        """증상 기반 질병 검색

        Args:
            query: 사용자 증상 설명
            top_k: 반환할 결과 수
            use_reranking: Cohere reranking 사용 여부

        Returns:
            유사도/관련성 순으로 정렬된 질병 결과
        """
        logger.info(f"🏥 질병 검색 쿼리: {query[:50]}...")

        # 쿼리 임베딩 (약품 검색과 동일한 임베딩 사용)
        query_embedding = await self.embedding_service.embed_text(query)

        # 질병 벡터 검색
        initial_top_k = top_k * 2 if (use_reranking and self.reranker.is_enabled()) else top_k
        results = await self.disease_vector_db.search_similar(query_embedding, initial_top_k)

        # Cohere Reranking (활성화된 경우)
        if use_reranking and self.reranker.is_enabled() and results:
            # 질병용 문서 텍스트 생성
            for r in results:
                r["document"] = f"질병: {r['name']}. 증상: {r['symptoms']}. 원인: {r['causes']}. 치료: {r['treatment']}"

            results = await self.reranker.rerank(
                query=query,
                documents=results,
                top_n=top_k,
            )

        # DiseaseResult로 변환
        disease_results = [
            DiseaseResult(
                disease_id=r["disease_id"],
                name=r["name"],
                name_en=r.get("name_en"),
                category=r.get("category"),
                description=r.get("description"),
                causes=r.get("causes"),
                symptoms=r.get("symptoms"),
                treatment=r.get("treatment"),
                prevention=r.get("prevention"),
                related_drugs=r.get("related_drugs"),
                similarity=r["similarity"],
                relevance_score=r.get("relevance_score"),
            )
            for r in results
        ]

        logger.info(f"✅ {len(disease_results)}개 질병 결과 반환")
        return disease_results

    async def search_and_generate(
        self,
        query: str,
        top_k: int = 5,
        include_diseases: bool = True,
    ) -> RAGResponse:
        """검색 + LLM 응답 생성 (질병 정보 포함)

        Args:
            query: 사용자 증상 설명
            top_k: 검색할 문서 수
            include_diseases: 질병 정보 포함 여부

        Returns:
            검색 결과 + 질병 정보 + AI 생성 응답
        """
        # 1. 의약품 검색
        drug_results = await self.search(query, top_k)

        # 2. 질병 검색 (활성화된 경우)
        disease_results = []
        if include_diseases:
            disease_results = await self.search_diseases(query, top_k=2)

        if not drug_results and not disease_results:
            return RAGResponse(
                results=[],
                disease_results=[],
                ai_response="죄송합니다. 관련 정보를 찾을 수 없습니다. 다른 증상으로 검색해 보시거나, 약사/의사와 상담하세요.",
            )

        # 3. 통합 컨텍스트 구성
        context = self.llm_service.format_integrated_context(
            drug_results=[
                {
                    "item_name": r.item_name,
                    "entp_name": r.entp_name,
                    "efficacy": r.efficacy,
                    "use_method": r.use_method,
                    "caution_info": r.caution_info,
                    "side_effects": r.side_effects,
                    "similarity": r.similarity,
                    "relevance_score": r.relevance_score,
                }
                for r in drug_results
            ],
            disease_results=[
                {
                    "name": d.name,
                    "category": d.category,
                    "description": d.description,
                    "causes": d.causes,
                    "symptoms": d.symptoms,
                    "treatment": d.treatment,
                    "prevention": d.prevention,
                    "related_drugs": d.related_drugs,
                    "similarity": d.similarity,
                    "relevance_score": d.relevance_score,
                }
                for d in disease_results
            ],
        )

        # 4. LLM 응답 생성
        try:
            ai_response = await self.llm_service.generate_integrated_response(query, context)
        except Exception as e:
            logger.error(f"LLM 응답 생성 실패: {e}")
            ai_response = "AI 응답을 생성할 수 없습니다. 아래 검색 결과를 참고해 주세요."

        return RAGResponse(
            results=drug_results,
            disease_results=disease_results,
            ai_response=ai_response,
        )

    async def get_similar_drugs(
        self,
        drug_id: str,
        top_k: int = 5,
    ) -> List[SearchResult]:
        """특정 의약품과 유사한 의약품 검색

        Args:
            drug_id: 기준 의약품 ID
            top_k: 반환할 결과 수

        Returns:
            유사한 의약품 목록
        """
        # TODO: 구현 - 해당 의약품의 벡터로 유사 검색
        raise NotImplementedError("유사 의약품 검색 기능은 아직 구현되지 않았습니다.")
