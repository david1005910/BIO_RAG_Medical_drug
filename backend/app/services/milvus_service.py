"""Milvus 벡터 데이터베이스 서비스 - Dense + Sparse Hybrid Search 지원"""
import logging
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    MilvusClient,
    connections,
    utility,
)

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class MilvusSearchResult:
    """Milvus 검색 결과"""

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


class MilvusService:
    """Milvus 벡터 데이터베이스 서비스

    Dense Vector (OpenAI Embedding) + Sparse Vector (BGE-M3) 하이브리드 검색 지원
    """

    # Field names
    DENSE_VECTOR_NAME = "dense"
    SPARSE_VECTOR_NAME = "sparse"

    def __init__(
        self,
        uri: Optional[str] = None,
        collection_name: Optional[str] = None,
        token: Optional[str] = None,
    ):
        self.uri = uri or settings.MILVUS_URI
        self.collection_name = collection_name or settings.MILVUS_COLLECTION_NAME
        self.token = token or settings.MILVUS_TOKEN
        self.client: Optional[MilvusClient] = None
        self._initialized = False

    async def connect(self) -> bool:
        """Milvus 서버에 연결

        Returns:
            연결 성공 여부
        """
        try:
            # MilvusClient API 사용 (pymilvus 2.4+)
            self.client = MilvusClient(
                uri=self.uri,
                token=self.token if self.token else None,
            )

            # 연결 테스트
            collections = self.client.list_collections()
            logger.info(f"✅ Milvus 연결 성공: {self.uri}")
            logger.info(f"📚 기존 컬렉션: {collections}")
            self._initialized = True
            return True
        except Exception as e:
            logger.error(f"❌ Milvus 연결 실패: {e}")
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
            if self.client.has_collection(self.collection_name):
                if recreate:
                    logger.info(f"🗑️ 기존 컬렉션 삭제: {self.collection_name}")
                    self.client.drop_collection(self.collection_name)
                else:
                    logger.info(f"📚 컬렉션 이미 존재: {self.collection_name}")
                    return True

            # 스키마 정의
            schema = self.client.create_schema(
                auto_id=False,
                enable_dynamic_field=True,
            )

            # Primary Key - drug_id의 UUID5 해시
            schema.add_field(
                field_name="id",
                datatype=DataType.VARCHAR,
                is_primary=True,
                max_length=64,
            )

            # 메타데이터 필드
            schema.add_field(
                field_name="drug_id",
                datatype=DataType.VARCHAR,
                max_length=64,
            )
            schema.add_field(
                field_name="item_name",
                datatype=DataType.VARCHAR,
                max_length=500,
            )
            schema.add_field(
                field_name="entp_name",
                datatype=DataType.VARCHAR,
                max_length=500,
            )
            schema.add_field(
                field_name="efficacy",
                datatype=DataType.VARCHAR,
                max_length=10000,
            )
            schema.add_field(
                field_name="use_method",
                datatype=DataType.VARCHAR,
                max_length=10000,
            )
            schema.add_field(
                field_name="caution_info",
                datatype=DataType.VARCHAR,
                max_length=10000,
            )
            schema.add_field(
                field_name="side_effects",
                datatype=DataType.VARCHAR,
                max_length=10000,
            )

            # Dense 벡터 필드 (OpenAI embedding)
            schema.add_field(
                field_name=self.DENSE_VECTOR_NAME,
                datatype=DataType.FLOAT_VECTOR,
                dim=dense_dim,
            )

            # Sparse 벡터 필드 (BGE-M3)
            schema.add_field(
                field_name=self.SPARSE_VECTOR_NAME,
                datatype=DataType.SPARSE_FLOAT_VECTOR,
            )

            # 인덱스 파라미터
            index_params = self.client.prepare_index_params()

            # Dense 벡터 인덱스 (HNSW for cosine similarity)
            index_params.add_index(
                field_name=self.DENSE_VECTOR_NAME,
                index_type="HNSW",
                metric_type="COSINE",
                params={"M": 16, "efConstruction": 200},
            )

            # Sparse 벡터 인덱스
            index_params.add_index(
                field_name=self.SPARSE_VECTOR_NAME,
                index_type="SPARSE_INVERTED_INDEX",
                metric_type="IP",  # Inner Product for sparse
                params={"drop_ratio_build": 0.2},
            )

            # 컬렉션 생성
            self.client.create_collection(
                collection_name=self.collection_name,
                schema=schema,
                index_params=index_params,
            )

            logger.info(f"✅ 컬렉션 생성 완료: {self.collection_name}")
            logger.info(f"   - Dense 벡터: {dense_dim}차원, HNSW, Cosine")
            logger.info(f"   - Sparse 벡터: SPARSE_INVERTED_INDEX, IP")
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
            sparse_vectors: Sparse 벡터 리스트 (BGE-M3)
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
            batch_docs = documents[i : i + batch_size]
            batch_dense = dense_vectors[i : i + batch_size]
            batch_sparse = sparse_vectors[i : i + batch_size]

            data = []
            for j, (doc, dense, sparse) in enumerate(
                zip(batch_docs, batch_dense, batch_sparse)
            ):
                # drug_id를 UUID5로 변환
                drug_id = str(doc.get("drug_id", f"doc_{i + j}"))
                point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, drug_id))

                # Sparse 벡터를 Milvus 형식으로 변환
                # Milvus expects {index: value, ...} dict format
                sparse_dict = {}
                indices = sparse.get("indices", [])
                values = sparse.get("values", [])
                for idx, val in zip(indices, values):
                    sparse_dict[int(idx)] = float(val)

                # 문자열 길이 제한 적용
                data.append(
                    {
                        "id": point_id,
                        "drug_id": drug_id,
                        "item_name": str(doc.get("item_name", ""))[:500],
                        "entp_name": str(doc.get("entp_name", ""))[:500],
                        "efficacy": str(doc.get("efficacy", ""))[:10000],
                        "use_method": str(doc.get("use_method", ""))[:10000],
                        "caution_info": str(doc.get("caution_info", ""))[:10000],
                        "side_effects": str(doc.get("side_effects", ""))[:10000],
                        self.DENSE_VECTOR_NAME: dense,
                        self.SPARSE_VECTOR_NAME: sparse_dict,
                    }
                )

            try:
                self.client.upsert(
                    collection_name=self.collection_name,
                    data=data,
                )
                total_upserted += len(data)
                logger.info(f"📝 배치 업서트: {len(data)}개 (총 {total_upserted}개)")
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
    ) -> List[MilvusSearchResult]:
        """하이브리드 검색 (Dense + Sparse)

        점수 체계:
        - Dense Score: 0~1 (코사인 유사도)
        - Sparse Score: BGE-M3 점수를 0~10 기준으로 0~1 정규화
        - Hybrid Score: dense * 0.7 + sparse * 0.3

        Args:
            dense_vector: 쿼리 Dense 벡터 (OpenAI embedding)
            sparse_vector: 쿼리 Sparse 벡터 (BGE-M3)
            top_k: 반환할 결과 수
            dense_weight: Dense 가중치 (기본 0.7)
            sparse_weight: Sparse 가중치 (기본 0.3)

        Returns:
            하이브리드 검색 결과 리스트
        """
        if not self.client:
            await self.connect()

        try:
            # Sparse 벡터를 Milvus 형식으로 변환
            sparse_dict = {}
            indices = sparse_vector.get("indices", [])
            values = sparse_vector.get("values", [])
            for idx, val in zip(indices, values):
                sparse_dict[int(idx)] = float(val)

            # 출력 필드
            output_fields = [
                "drug_id",
                "item_name",
                "entp_name",
                "efficacy",
                "use_method",
                "caution_info",
                "side_effects",
            ]

            # Dense 검색 수행
            dense_results = self.client.search(
                collection_name=self.collection_name,
                data=[dense_vector],
                anns_field=self.DENSE_VECTOR_NAME,
                search_params={"metric_type": "COSINE", "params": {"ef": 100}},
                limit=top_k * 2,
                output_fields=output_fields,
            )

            # Sparse 검색 수행
            sparse_results = self.client.search(
                collection_name=self.collection_name,
                data=[sparse_dict],
                anns_field=self.SPARSE_VECTOR_NAME,
                search_params={"metric_type": "IP", "params": {"drop_ratio_search": 0.2}},
                limit=top_k * 2,
                output_fields=output_fields,
            )

            # 결과 병합 및 하이브리드 점수 계산
            results_map: Dict[str, Dict] = {}

            # Dense 결과 처리
            if dense_results and len(dense_results) > 0:
                for hit in dense_results[0]:
                    entity = hit.get("entity", {})
                    drug_id = entity.get("drug_id", str(hit.get("id", "")))
                    # Cosine similarity score
                    dense_score = float(hit.get("distance", 0))

                    results_map[drug_id] = {
                        "entity": entity,
                        "id": hit.get("id"),
                        "dense_score": dense_score,
                        "sparse_score": 0.0,
                    }

            # Sparse 결과 처리
            splade_max_score = settings.SPLADE_MAX_SCORE

            if sparse_results and len(sparse_results) > 0:
                for hit in sparse_results[0]:
                    entity = hit.get("entity", {})
                    drug_id = entity.get("drug_id", str(hit.get("id", "")))
                    raw_sparse_score = float(hit.get("distance", 0))
                    sparse_score = min(raw_sparse_score / splade_max_score, 1.0)

                    if drug_id in results_map:
                        results_map[drug_id]["sparse_score"] = sparse_score
                    else:
                        results_map[drug_id] = {
                            "entity": entity,
                            "id": hit.get("id"),
                            "dense_score": 0.0,
                            "sparse_score": sparse_score,
                        }

            # 하이브리드 점수 계산 및 결과 생성
            hybrid_results = []
            for drug_id, data in results_map.items():
                dense_score = data["dense_score"]
                sparse_score = data["sparse_score"]

                # Hybrid Score = sparse * weight + dense * weight
                hybrid_score = sparse_weight * sparse_score + dense_weight * dense_score

                entity = data.get("entity", {})
                hybrid_results.append(
                    MilvusSearchResult(
                        drug_id=entity.get("drug_id", drug_id),
                        item_name=entity.get("item_name", ""),
                        entp_name=entity.get("entp_name", ""),
                        efficacy=entity.get("efficacy", ""),
                        use_method=entity.get("use_method"),
                        caution_info=entity.get("caution_info"),
                        side_effects=entity.get("side_effects"),
                        dense_score=dense_score,
                        sparse_score=sparse_score,
                        hybrid_score=hybrid_score,
                    )
                )

            # 하이브리드 점수로 정렬
            hybrid_results.sort(key=lambda x: x.hybrid_score, reverse=True)

            logger.info(
                f"🔀 Milvus Hybrid 검색 완료: "
                f"Dense={len(dense_results[0]) if dense_results else 0}, "
                f"Sparse={len(sparse_results[0]) if sparse_results else 0}, "
                f"Merged={len(hybrid_results[:top_k])}"
            )

            return hybrid_results[:top_k]

        except Exception as e:
            logger.error(f"❌ Milvus Hybrid 검색 실패: {e}")
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
            output_fields = [
                "drug_id",
                "item_name",
                "entp_name",
                "efficacy",
                "use_method",
                "caution_info",
                "side_effects",
            ]

            results = self.client.search(
                collection_name=self.collection_name,
                data=[dense_vector],
                anns_field=self.DENSE_VECTOR_NAME,
                search_params={"metric_type": "COSINE", "params": {"ef": 100}},
                limit=top_k,
                output_fields=output_fields,
            )

            if results and len(results) > 0:
                return [
                    {
                        "drug_id": hit.get("entity", {}).get(
                            "drug_id", str(hit.get("id", ""))
                        ),
                        "similarity": float(hit.get("distance", 0)),
                        "dense_score": float(hit.get("distance", 0)),
                        **hit.get("entity", {}),
                    }
                    for hit in results[0]
                ]
            return []

        except Exception as e:
            logger.error(f"❌ Dense 검색 실패: {e}")
            return []

    async def get_collection_info(self) -> Optional[Dict]:
        """컬렉션 정보 조회"""
        if not self.client:
            await self.connect()

        try:
            stats = self.client.get_collection_stats(self.collection_name)
            return {
                "name": self.collection_name,
                "points_count": stats.get("row_count", 0),
                "vectors_count": stats.get("row_count", 0),
                "status": "ready",
            }
        except Exception as e:
            logger.error(f"❌ 컬렉션 정보 조회 실패: {e}")
            return None

    async def delete_collection(self) -> bool:
        """컬렉션 삭제"""
        if not self.client:
            await self.connect()

        try:
            self.client.drop_collection(self.collection_name)
            logger.info(f"🗑️ 컬렉션 삭제 완료: {self.collection_name}")
            return True
        except Exception as e:
            logger.error(f"❌ 컬렉션 삭제 실패: {e}")
            return False


# 싱글톤 인스턴스
_milvus_service: Optional[MilvusService] = None


def get_milvus_service() -> MilvusService:
    """Milvus 서비스 싱글톤 반환"""
    global _milvus_service
    if _milvus_service is None:
        _milvus_service = MilvusService()
    return _milvus_service


async def initialize_milvus() -> bool:
    """Milvus 초기화 - 연결 및 컬렉션 생성"""
    if not settings.ENABLE_MILVUS:
        logger.info("⚠️ Milvus 비활성화됨 (ENABLE_MILVUS=false)")
        return False

    service = get_milvus_service()
    connected = await service.connect()

    if connected:
        await service.create_collection(
            dense_dim=settings.EMBEDDING_DIMENSIONS,
            recreate=False,
        )
        return True

    return False
