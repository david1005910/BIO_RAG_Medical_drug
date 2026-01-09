"""Qdrant 벡터 데이터베이스 서비스 - Dense + Sparse Hybrid Search 지원"""
import logging
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    PointStruct,
    SparseVector,
    SparseVectorParams,
    VectorParams,
)

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class QdrantSearchResult:
    """Qdrant 검색 결과"""
    drug_id: str
    item_name: str
    entp_name: str
    efficacy: str
    use_method: Optional[str]
    caution_info: Optional[str]
    side_effects: Optional[str]
    dense_score: float
    sparse_score: float
    hybrid_score: float


class QdrantService:
    """Qdrant 벡터 데이터베이스 서비스

    Dense Vector (OpenAI Embedding) + Sparse Vector (SPLADE) 하이브리드 검색 지원
    """

    DENSE_VECTOR_NAME = "dense"
    SPARSE_VECTOR_NAME = "sparse"

    def __init__(
        self,
        url: Optional[str] = None,
        collection_name: Optional[str] = None,
    ):
        self.url = url or settings.QDRANT_URL
        self.collection_name = collection_name or settings.QDRANT_COLLECTION_NAME
        self.client: Optional[QdrantClient] = None
        self._initialized = False

    async def connect(self) -> bool:
        """Qdrant 서버에 연결

        Returns:
            연결 성공 여부
        """
        try:
            self.client = QdrantClient(url=self.url)
            # 연결 테스트
            collections = self.client.get_collections()
            logger.info(f"✅ Qdrant 연결 성공: {self.url}")
            logger.info(f"📚 기존 컬렉션: {[c.name for c in collections.collections]}")
            self._initialized = True
            return True
        except Exception as e:
            logger.error(f"❌ Qdrant 연결 실패: {e}")
            self._initialized = False
            return False

    async def create_collection(
        self,
        dense_dim: int = 1536,
        recreate: bool = False,
    ) -> bool:
        """컬렉션 생성 (Dense + Sparse 벡터)

        Args:
            dense_dim: Dense 벡터 차원 (OpenAI embedding: 1536)
            recreate: 기존 컬렉션 삭제 후 재생성 여부

        Returns:
            생성 성공 여부
        """
        if not self.client:
            await self.connect()

        try:
            # 기존 컬렉션 확인
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if self.collection_name in collection_names:
                if recreate:
                    logger.info(f"🗑️ 기존 컬렉션 삭제: {self.collection_name}")
                    self.client.delete_collection(self.collection_name)
                else:
                    logger.info(f"📚 컬렉션 이미 존재: {self.collection_name}")
                    return True

            # 새 컬렉션 생성 (Dense + Sparse 벡터)
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config={
                    self.DENSE_VECTOR_NAME: VectorParams(
                        size=dense_dim,
                        distance=Distance.COSINE,
                    ),
                },
                sparse_vectors_config={
                    self.SPARSE_VECTOR_NAME: SparseVectorParams(),
                },
            )

            logger.info(f"✅ 컬렉션 생성 완료: {self.collection_name}")
            logger.info(f"   - Dense 벡터: {dense_dim}차원, Cosine Distance")
            logger.info("   - Sparse 벡터: SPLADE")
            return True

        except Exception as e:
            logger.error(f"❌ 컬렉션 생성 실패: {e}")
            return False

    async def upsert_documents(
        self,
        documents: List[Dict[str, Any]],
        dense_vectors: List[List[float]],
        sparse_vectors: List[Dict[str, Any]],  # {"indices": [...], "values": [...]}
        batch_size: int = 100,
    ) -> int:
        """문서 및 벡터 업서트

        Args:
            documents: 문서 메타데이터 리스트
            dense_vectors: Dense 벡터 리스트 (OpenAI embedding)
            sparse_vectors: Sparse 벡터 리스트 (SPLADE)
            batch_size: 배치 크기

        Returns:
            업서트된 문서 수
        """
        if not self.client:
            await self.connect()

        if len(documents) != len(dense_vectors) or len(documents) != len(sparse_vectors):
            logger.error("문서, Dense 벡터, Sparse 벡터 수가 일치하지 않습니다.")
            return 0

        total_upserted = 0

        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i:i + batch_size]
            batch_dense = dense_vectors[i:i + batch_size]
            batch_sparse = sparse_vectors[i:i + batch_size]

            points = []
            for j, (doc, dense, sparse) in enumerate(zip(batch_docs, batch_dense, batch_sparse)):
                # drug_id를 UUID5로 변환 (일관된 ID 생성)
                drug_id = str(doc.get("drug_id", f"doc_{i + j}"))
                point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, drug_id))

                # Sparse 벡터 생성
                sparse_vector = SparseVector(
                    indices=sparse.get("indices", []),
                    values=sparse.get("values", []),
                )

                points.append(
                    PointStruct(
                        id=point_id,
                        vector={
                            self.DENSE_VECTOR_NAME: dense,
                            self.SPARSE_VECTOR_NAME: sparse_vector,
                        },
                        payload={
                            "drug_id": doc.get("drug_id"),
                            "item_name": doc.get("item_name", ""),
                            "entp_name": doc.get("entp_name", ""),
                            "efficacy": doc.get("efficacy", ""),
                            "use_method": doc.get("use_method", ""),
                            "caution_info": doc.get("caution_info", ""),
                            "side_effects": doc.get("side_effects", ""),
                        },
                    )
                )

            try:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=points,
                )
                total_upserted += len(points)
                logger.info(f"📝 배치 업서트: {len(points)}개 (총 {total_upserted}개)")
            except Exception as e:
                logger.error(f"❌ 배치 업서트 실패: {e}")

        logger.info(f"✅ 전체 업서트 완료: {total_upserted}개")
        return total_upserted

    async def hybrid_search(
        self,
        dense_vector: List[float],
        sparse_vector: Dict[str, Any],  # {"indices": [...], "values": [...]}
        top_k: int = 10,
        dense_weight: float = 0.7,
        sparse_weight: float = 0.3,
    ) -> List[QdrantSearchResult]:
        """하이브리드 검색 (Dense + Sparse)

        점수 체계:
        - Dense Score: 0~1 (코사인 유사도)
        - Sparse Score: SPLADE 점수를 0~30 기준으로 0~1 정규화
        - Hybrid Score: dense * 0.7 + sparse * 0.3

        Args:
            dense_vector: 쿼리 Dense 벡터 (OpenAI embedding)
            sparse_vector: 쿼리 Sparse 벡터 (SPLADE)
            top_k: 반환할 결과 수
            dense_weight: Dense 가중치 (기본 0.3)
            sparse_weight: Sparse 가중치 (기본 0.7)

        Returns:
            하이브리드 검색 결과 리스트
        """
        if not self.client:
            await self.connect()

        try:
            # Dense 검색 (query_points 사용 - qdrant-client 1.x)
            dense_response = self.client.query_points(
                collection_name=self.collection_name,
                query=dense_vector,
                using=self.DENSE_VECTOR_NAME,
                limit=top_k * 2,
                with_payload=True,
            )
            dense_results = dense_response.points

            # Sparse 검색
            sparse_query = SparseVector(
                indices=sparse_vector.get("indices", []),
                values=sparse_vector.get("values", []),
            )

            sparse_response = self.client.query_points(
                collection_name=self.collection_name,
                query=sparse_query,
                using=self.SPARSE_VECTOR_NAME,
                limit=top_k * 2,
                with_payload=True,
            )
            sparse_results = sparse_response.points

            # 결과 병합 및 하이브리드 점수 계산
            results_map: Dict[str, Dict] = {}

            # Dense 결과 처리
            for result in dense_results:
                drug_id = str(result.id)
                dense_score = result.score  # 코사인 유사도 (0~1)

                results_map[drug_id] = {
                    "payload": result.payload,
                    "dense_score": dense_score,
                    "sparse_score": 0.0,
                }

            # Sparse 결과 처리
            # SPLADE 점수 정규화: 0~30 기준으로 0~1로 정규화
            splade_max_score = settings.SPLADE_MAX_SCORE

            for result in sparse_results:
                drug_id = str(result.id)
                raw_sparse_score = result.score
                # SPLADE 점수 정규화 (30점 기준)
                sparse_score = min(raw_sparse_score / splade_max_score, 1.0)

                if drug_id in results_map:
                    results_map[drug_id]["sparse_score"] = sparse_score
                else:
                    results_map[drug_id] = {
                        "payload": result.payload,
                        "dense_score": 0.0,
                        "sparse_score": sparse_score,
                    }

            # 하이브리드 점수 계산 및 결과 생성
            hybrid_results = []
            for drug_id, data in results_map.items():
                dense_score = data["dense_score"]
                sparse_score = data["sparse_score"]

                # Hybrid Score = sparse * 0.7 + dense * 0.3
                hybrid_score = (
                    sparse_weight * sparse_score +
                    dense_weight * dense_score
                )

                payload = data["payload"]
                hybrid_results.append(
                    QdrantSearchResult(
                        drug_id=drug_id,
                        item_name=payload.get("item_name", ""),
                        entp_name=payload.get("entp_name", ""),
                        efficacy=payload.get("efficacy", ""),
                        use_method=payload.get("use_method"),
                        caution_info=payload.get("caution_info"),
                        side_effects=payload.get("side_effects"),
                        dense_score=dense_score,
                        sparse_score=sparse_score,
                        hybrid_score=hybrid_score,
                    )
                )

            # 하이브리드 점수로 정렬
            hybrid_results.sort(key=lambda x: x.hybrid_score, reverse=True)

            logger.info(
                f"🔀 Qdrant Hybrid 검색 완료: "
                f"Dense={len(dense_results)}, Sparse={len(sparse_results)}, "
                f"Merged={len(hybrid_results[:top_k])}"
            )

            return hybrid_results[:top_k]

        except Exception as e:
            logger.error(f"❌ Qdrant Hybrid 검색 실패: {e}")
            return []

    async def dense_search(
        self,
        dense_vector: List[float],
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """Dense 벡터 검색만 수행

        Args:
            dense_vector: 쿼리 Dense 벡터
            top_k: 반환할 결과 수

        Returns:
            검색 결과 리스트
        """
        if not self.client:
            await self.connect()

        try:
            response = self.client.query_points(
                collection_name=self.collection_name,
                query=dense_vector,
                using=self.DENSE_VECTOR_NAME,
                limit=top_k,
                with_payload=True,
            )

            return [
                {
                    "drug_id": str(r.id),
                    "similarity": r.score,
                    "dense_score": r.score,
                    **r.payload,
                }
                for r in response.points
            ]

        except Exception as e:
            logger.error(f"❌ Dense 검색 실패: {e}")
            return []

    async def get_collection_info(self) -> Optional[Dict]:
        """컬렉션 정보 조회"""
        if not self.client:
            await self.connect()

        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "name": self.collection_name,
                "points_count": info.points_count,
                "vectors_count": info.vectors_count,
                "status": info.status.value,
            }
        except Exception as e:
            logger.error(f"❌ 컬렉션 정보 조회 실패: {e}")
            return None

    async def delete_collection(self) -> bool:
        """컬렉션 삭제"""
        if not self.client:
            await self.connect()

        try:
            self.client.delete_collection(self.collection_name)
            logger.info(f"🗑️ 컬렉션 삭제 완료: {self.collection_name}")
            return True
        except Exception as e:
            logger.error(f"❌ 컬렉션 삭제 실패: {e}")
            return False


# 싱글톤 인스턴스
_qdrant_service: Optional[QdrantService] = None


def get_qdrant_service() -> QdrantService:
    """Qdrant 서비스 싱글톤 반환"""
    global _qdrant_service
    if _qdrant_service is None:
        _qdrant_service = QdrantService()
    return _qdrant_service


async def initialize_qdrant() -> bool:
    """Qdrant 초기화 - 연결 및 컬렉션 생성"""
    if not settings.ENABLE_QDRANT:
        logger.info("⚠️ Qdrant 비활성화됨 (ENABLE_QDRANT=false)")
        return False

    service = get_qdrant_service()
    connected = await service.connect()

    if connected:
        await service.create_collection(
            dense_dim=settings.EMBEDDING_DIMENSIONS,
            recreate=False,
        )
        return True

    return False
