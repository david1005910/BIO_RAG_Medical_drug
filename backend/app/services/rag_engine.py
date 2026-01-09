"""RAG 엔진 - 검색 + 생성 통합

검색 모드:
- Milvus 모드 (ENABLE_MILVUS=true): Milvus Dense + SPLADE Hybrid 검색
- 기본 모드: PGVector Dense 벡터 검색

점수 체계:
- Dense Score: 0~1 (코사인 유사도)
- Sparse Score: 0~1 (BGE-M3 SPLADE, 10점 기준 정규화)
- Hybrid Score: dense * 0.7 + sparse * 0.3
"""
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.embedding import get_embedding_service, EmbeddingService
from app.services.vector_db import VectorDBService
from app.services.disease_vector_db import DiseaseVectorDBService
from app.services.llm_service import get_llm_service, LLMService
from app.services.milvus_service import get_milvus_service, MilvusService
from app.services.splade_service import get_splade_service, SPLADEService
from app.external.cohere_client import get_reranker, CohereReranker
from app.services.neo4j_service import get_neo4j_service, Neo4jService

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
    dense_score: Optional[float] = None  # Dense(벡터) 검색 정규화 점수
    bm25_score: Optional[float] = None  # BM25(키워드) 검색 정규화 점수
    hybrid_score: Optional[float] = None  # Hybrid(Dense+BM25) 결합 점수


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
class InteractionWarning:
    """약물 상호작용 경고 데이터 클래스"""

    drug_id_1: str
    drug_name_1: str
    drug_id_2: str
    drug_name_2: str
    interaction_type: str
    severity: int
    description: Optional[str] = None


@dataclass
class GraphEnhancement:
    """그래프 기반 검색 강화 데이터"""

    related_drugs: List[Dict[str, Any]] = field(default_factory=list)
    interaction_warnings: List[InteractionWarning] = field(default_factory=list)
    symptom_drugs: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class RAGResponse:
    """RAG 응답 데이터 클래스"""

    results: List[SearchResult]
    disease_results: Optional[List[DiseaseResult]] = None
    ai_response: Optional[str] = None
    graph_data: Optional[GraphEnhancement] = None
    disclaimer: str = "※ 이 정보는 참고용입니다. 실제 복약은 의사/약사와 상담하세요."


class RAGEngine:
    """의약품 + 질병 정보 RAG 엔진

    검색(Retrieval) + 재순위(Reranking) + 생성(Generation)을 통합한 핵심 엔진
    Dense + Sparse(SPLADE) 하이브리드 검색 기반 의미적 + 키워드 매칭

    검색 모드:
    - Milvus 모드 (ENABLE_MILVUS=true): Milvus Dense + SPLADE Hybrid 검색
    - 기본 모드: PGVector Dense 벡터 검색
    """

    def __init__(
        self,
        session: AsyncSession,
        embedding_service: Optional[EmbeddingService] = None,
        llm_service: Optional[LLMService] = None,
        reranker: Optional[CohereReranker] = None,
        milvus_service: Optional[MilvusService] = None,
        splade_service: Optional[SPLADEService] = None,
        neo4j_service: Optional[Neo4jService] = None,
    ):
        self.session = session
        self.vector_db = VectorDBService(session)
        self.disease_vector_db = DiseaseVectorDBService(session)
        self.embedding_service = embedding_service or get_embedding_service()
        self.llm_service = llm_service or get_llm_service()
        self.reranker = reranker or get_reranker()

        # Milvus Hybrid 검색 설정 (Dense + SPLADE)
        self.enable_milvus = settings.ENABLE_MILVUS
        if self.enable_milvus:
            self.milvus_service = milvus_service or get_milvus_service()
            self.splade_service = splade_service or get_splade_service()
            logger.info("🚀 Milvus Dense + SPLADE Hybrid 검색 모드 활성화")
        else:
            self.milvus_service = None
            self.splade_service = None
            logger.info("🔀 PGVector Dense 벡터 검색 모드 활성화")

        # Neo4j 그래프 서비스 설정
        self.enable_neo4j = settings.ENABLE_NEO4J
        if self.enable_neo4j:
            self.neo4j_service = neo4j_service or get_neo4j_service()
            logger.info("🔗 Neo4j 그래프 검색 강화 활성화")
        else:
            self.neo4j_service = None

    async def search(
        self,
        query: str,
        top_k: int = 5,
        use_reranking: bool = True,
        query_embedding: Optional[List[float]] = None,
    ) -> List[SearchResult]:
        """증상 기반 의약품 검색 (LLM 응답 없음)

        검색 모드:
        - Qdrant 모드: Qdrant Dense + SPLADE Hybrid 검색
        - 기본 모드: PGVector Dense 벡터 검색

        Args:
            query: 사용자 증상 설명
            top_k: 반환할 결과 수
            use_reranking: Cohere reranking 사용 여부
            query_embedding: 사전 계산된 쿼리 임베딩 (재사용용)

        Returns:
            유사도/관련성 순으로 정렬된 검색 결과
        """
        logger.info(f"🔍 검색 쿼리: {query[:50]}...")

        # reranking 사용시 더 많이 가져옴
        expand_factor = 5 if (use_reranking and self.reranker.is_enabled()) else 3
        initial_top_k = top_k * expand_factor

        # Milvus Hybrid 검색 모드 (Dense + SPLADE)
        if self.enable_milvus and self.milvus_service:
            logger.info("🚀 Milvus Dense + SPLADE Hybrid 검색")
            results = await self._search_with_milvus_hybrid(
                query=query,
                top_k=initial_top_k,
                query_embedding=query_embedding,
            )
        else:
            # PGVector Dense 검색 모드
            results = await self._search_with_pgvector(
                query=query,
                top_k=initial_top_k,
                query_embedding=query_embedding,
            )

        # Cohere Reranking (활성화된 경우)
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

        # SearchResult로 변환
        search_results = [
            SearchResult(
                drug_id=r["drug_id"],
                item_name=r["item_name"],
                entp_name=r["entp_name"],
                efficacy=r["efficacy"],
                use_method=r["use_method"],
                caution_info=r["caution_info"],
                side_effects=r["side_effects"],
                similarity=r.get("hybrid_score", r.get("similarity", r.get("dense_score", 0))),
                relevance_score=r.get("relevance_score"),
                dense_score=r.get("dense_score"),
                bm25_score=r.get("sparse_score"),  # SPLADE sparse score
                hybrid_score=r.get("hybrid_score"),
            )
            for r in results
        ]

        # 로그에 검색 방식 표시
        search_type = ["Milvus+SPLADE" if self.enable_milvus else "PGVector"]
        if use_reranking and self.reranker.is_enabled():
            search_type.append("Reranking")

        logger.info(f"✅ {len(search_results)}개 결과 반환 [{'+'.join(search_type)}]")
        return search_results

    async def _search_with_milvus_hybrid(
        self,
        query: str,
        top_k: int,
        query_embedding: Optional[List[float]] = None,
    ) -> List[Dict]:
        """Milvus Dense + SPLADE Hybrid 검색

        Args:
            query: 검색 쿼리
            top_k: 반환할 결과 수
            query_embedding: 사전 계산된 쿼리 임베딩

        Returns:
            검색 결과 딕셔너리 리스트
        """
        try:
            # 쿼리 임베딩 (Dense) - 제공되지 않은 경우에만 생성
            if query_embedding is None:
                query_embedding = await self.embedding_service.embed_text(query)

            # SPLADE sparse 임베딩 생성 (쿼리 확장 포함)
            sparse_vector = await self.splade_service.encode(query, expand=True)

            # Milvus Hybrid 검색 (Dense + Sparse)
            results = await self.milvus_service.hybrid_search(
                dense_vector=query_embedding,
                sparse_vector=sparse_vector,
                top_k=top_k,
            )

            # MilvusSearchResult를 Dict로 변환
            result_dicts = []
            for r in results:
                result_dicts.append({
                    "drug_id": r.drug_id,
                    "item_name": r.item_name,
                    "entp_name": r.entp_name,
                    "efficacy": r.efficacy,
                    "use_method": r.use_method,
                    "caution_info": r.caution_info,
                    "side_effects": r.side_effects,
                    "dense_score": r.dense_score,
                    "sparse_score": r.sparse_score,
                    "hybrid_score": r.hybrid_score,
                    "similarity": r.hybrid_score,
                })

            logger.info(f"✅ Milvus Hybrid 검색 완료: {len(result_dicts)}개 결과")
            return result_dicts

        except Exception as e:
            logger.warning(f"⚠️ Milvus Hybrid 검색 실패, PGVector로 폴백: {e}")
            # 폴백: PGVector Dense 검색
            return await self._search_with_pgvector(query, top_k, query_embedding)

    async def _search_with_pgvector(
        self,
        query: str,
        top_k: int,
        query_embedding: Optional[List[float]] = None,
    ) -> List[Dict]:
        """PGVector Dense 벡터 검색

        Args:
            query: 검색 쿼리
            top_k: 반환할 결과 수
            query_embedding: 사전 계산된 쿼리 임베딩

        Returns:
            검색 결과 딕셔너리 리스트
        """
        # 쿼리 임베딩 - 제공되지 않은 경우에만 생성
        if query_embedding is None:
            query_embedding = await self.embedding_service.embed_text(query)

        # PGVector Dense 검색
        results = await self.vector_db.search_similar(query_embedding, top_k)

        # dense_score 필드 추가
        for r in results:
            r["dense_score"] = r.get("similarity", 0)

        logger.info(f"✅ PGVector Dense 검색 완료: {len(results)}개 결과")
        return results

    async def search_diseases(
        self,
        query: str,
        top_k: int = 3,
        use_reranking: bool = True,
        query_embedding: Optional[List[float]] = None,
    ) -> List[DiseaseResult]:
        """증상 기반 질병 검색

        Args:
            query: 사용자 증상 설명
            top_k: 반환할 결과 수
            use_reranking: Cohere reranking 사용 여부
            query_embedding: 사전 계산된 쿼리 임베딩

        Returns:
            유사도/관련성 순으로 정렬된 질병 결과
        """
        logger.info(f"🏥 질병 검색 쿼리: {query[:50]}...")

        # 쿼리 임베딩 - 제공되지 않은 경우에만 생성
        if query_embedding is None:
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
        include_graph: bool = True,
    ) -> RAGResponse:
        """검색 + LLM 응답 생성 (질병 정보 + 그래프 정보 포함)

        Args:
            query: 사용자 증상 설명
            top_k: 검색할 문서 수
            include_diseases: 질병 정보 포함 여부
            include_graph: 그래프 정보 포함 여부

        Returns:
            검색 결과 + 질병 정보 + 그래프 정보 + AI 생성 응답
        """
        # 1. 쿼리 임베딩 생성 (한 번만 - 검색 최적화)
        query_embedding = await self.embedding_service.embed_text(query)

        # 2. 의약품 검색 + 질병 검색 (순차 실행 - 세션 동시성 문제 방지)
        # Note: 같은 DB 세션을 사용하므로 병렬 실행 시 SQLAlchemy 세션 충돌 발생
        drug_results = await self.search(query, top_k, query_embedding=query_embedding)

        if include_diseases:
            disease_results = await self.search_diseases(query, top_k=2, query_embedding=query_embedding)
        else:
            disease_results = []

        if not drug_results and not disease_results:
            return RAGResponse(
                results=[],
                disease_results=[],
                ai_response="죄송합니다. 관련 정보를 찾을 수 없습니다. 다른 증상으로 검색해 보시거나, 약사/의사와 상담하세요.",
            )

        # 3. 그래프 강화 데이터 조회 (활성화된 경우)
        graph_data = None
        graph_context = ""
        if include_graph and self.enable_neo4j:
            drug_ids = [r.drug_id for r in drug_results]
            graph_data = await self._get_graph_enhancement(drug_ids)
            graph_context = self._format_graph_context(graph_data)

        # 4. 통합 컨텍스트 구성
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

        # 그래프 컨텍스트 추가
        if graph_context:
            context += graph_context

        # 5. LLM 응답 생성
        try:
            ai_response = await self.llm_service.generate_integrated_response(query, context)
        except Exception as e:
            logger.error(f"LLM 응답 생성 실패: {e}")
            ai_response = "AI 응답을 생성할 수 없습니다. 아래 검색 결과를 참고해 주세요."

        return RAGResponse(
            results=drug_results,
            disease_results=disease_results,
            ai_response=ai_response,
            graph_data=graph_data,
        )

    async def _get_graph_enhancement(
        self,
        drug_ids: List[str],
        symptoms: Optional[List[str]] = None,
    ) -> GraphEnhancement:
        """그래프 기반 검색 강화 데이터 조회

        Args:
            drug_ids: 검색된 약물 ID 목록
            symptoms: 추출된 증상 목록 (선택)

        Returns:
            그래프 강화 데이터 (관련 약물, 상호작용 경고, 증상별 약물)
        """
        if not self.enable_neo4j or not self.neo4j_service:
            return GraphEnhancement()

        try:
            logger.info(f"🔗 그래프 검색 강화 중... (약물 {len(drug_ids)}개)")

            # 1. 약물 간 상호작용 조회
            interaction_warnings = []
            if len(drug_ids) >= 2:
                cross_interactions = await self.neo4j_service.get_cross_interactions(drug_ids)
                for interaction in cross_interactions:
                    # interaction.item_name에는 "약물1 ↔ 약물2" 형태로 저장됨
                    names = interaction.item_name.split(" ↔ ")
                    if len(names) == 2:
                        interaction_warnings.append(
                            InteractionWarning(
                                drug_id_1=interaction.drug_id.split("_")[0] if "_" in interaction.drug_id else drug_ids[0],
                                drug_name_1=names[0],
                                drug_id_2=interaction.drug_id.split("_")[1] if "_" in interaction.drug_id else drug_ids[1],
                                drug_name_2=names[1],
                                interaction_type=interaction.interaction_type,
                                severity=interaction.severity,
                                description=interaction.description,
                            )
                        )

            # 2. 검색된 각 약물의 관련 약물 조회 (상위 3개씩)
            related_drugs = []
            for drug_id in drug_ids[:3]:  # 상위 3개 약물만
                related = await self.neo4j_service.get_related_drugs(drug_id, limit=3)
                for r in related:
                    if r.drug_id not in drug_ids:  # 중복 제외
                        related_drugs.append({
                            "drug_id": r.drug_id,
                            "item_name": r.item_name,
                            "relationship_type": r.relationship_type,
                            "score": r.score,
                            "source_drug_id": drug_id,
                        })

            # 3. 증상별 약물 조회 (증상이 주어진 경우)
            symptom_drugs = []
            if symptoms:
                for symptom in symptoms[:2]:  # 상위 2개 증상만
                    drugs = await self.neo4j_service.get_drugs_for_symptom(symptom, limit=3)
                    for d in drugs:
                        if d["drug_id"] not in drug_ids:  # 중복 제외
                            symptom_drugs.append({
                                "drug_id": d["drug_id"],
                                "item_name": d["item_name"],
                                "symptom": symptom,
                                "effectiveness": d.get("effectiveness", 0.5),
                            })

            logger.info(
                f"✅ 그래프 강화 완료: 상호작용 {len(interaction_warnings)}개, "
                f"관련 약물 {len(related_drugs)}개, 증상 약물 {len(symptom_drugs)}개"
            )

            return GraphEnhancement(
                related_drugs=related_drugs,
                interaction_warnings=interaction_warnings,
                symptom_drugs=symptom_drugs,
            )

        except Exception as e:
            logger.warning(f"⚠️ 그래프 강화 실패: {e}")
            return GraphEnhancement()

    def _format_graph_context(self, graph_data: GraphEnhancement) -> str:
        """그래프 데이터를 LLM 컨텍스트용 텍스트로 변환

        Args:
            graph_data: 그래프 강화 데이터

        Returns:
            LLM 컨텍스트용 포맷된 텍스트
        """
        if not graph_data.interaction_warnings and not graph_data.related_drugs:
            return ""

        lines = ["\n[약물 관계 정보]"]

        # 상호작용 경고
        if graph_data.interaction_warnings:
            lines.append("\n⚠️ 상호작용 주의:")
            for warn in graph_data.interaction_warnings:
                severity_text = {1: "약함", 2: "보통", 3: "주의", 4: "경고", 5: "위험"}.get(
                    warn.severity, "알 수 없음"
                )
                lines.append(
                    f"  - {warn.drug_name_1} ↔ {warn.drug_name_2}: {warn.interaction_type} (위험도: {severity_text})"
                )
                if warn.description:
                    lines.append(f"    설명: {warn.description[:100]}...")

        # 관련 약물
        if graph_data.related_drugs:
            lines.append("\n🔗 관련 약물:")
            seen = set()
            for drug in graph_data.related_drugs:
                if drug["drug_id"] not in seen:
                    seen.add(drug["drug_id"])
                    lines.append(
                        f"  - {drug['item_name']} ({drug['relationship_type']}, 관련도: {drug['score']:.2f})"
                    )

        return "\n".join(lines)

    async def search_with_graph_enhancement(
        self,
        query: str,
        top_k: int = 5,
        use_reranking: bool = True,
        symptoms: Optional[List[str]] = None,
    ) -> tuple[List[SearchResult], GraphEnhancement]:
        """그래프 강화된 검색

        Args:
            query: 사용자 증상 설명
            top_k: 반환할 결과 수
            use_reranking: Cohere reranking 사용 여부
            symptoms: 증상 목록 (증상 기반 약물 추천용)

        Returns:
            (검색 결과, 그래프 강화 데이터) 튜플
        """
        # 1. 기본 검색
        search_results = await self.search(query, top_k, use_reranking)

        # 2. 그래프 강화 데이터 조회
        drug_ids = [r.drug_id for r in search_results]
        graph_data = await self._get_graph_enhancement(drug_ids, symptoms)

        return search_results, graph_data

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
        # Neo4j 그래프에서 유사 약물 조회
        if self.enable_neo4j and self.neo4j_service:
            related = await self.neo4j_service.get_related_drugs(drug_id, limit=top_k)
            # TODO: related에서 약물 상세 정보 조회하여 SearchResult로 변환
            logger.info(f"🔗 Neo4j에서 유사 약물 {len(related)}개 조회")

        # TODO: 해당 의약품의 벡터로 유사 검색 구현
        raise NotImplementedError("유사 의약품 검색 기능은 아직 구현되지 않았습니다.")
