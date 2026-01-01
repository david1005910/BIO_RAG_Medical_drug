"""데이터 동기화 서비스 - API → DB → Vector Index (PGVector + Qdrant)"""
import logging
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.external.data_go_kr import DataGoKrClient, DrugInfo
from app.models.drug import Drug
from app.services.data_preprocessor import DrugDataPreprocessor
from app.services.embedding import get_embedding_service
from app.services.vector_db import VectorDBService
from app.services.qdrant_service import get_qdrant_service
from app.services.splade_service import get_splade_service
from app.core.config import settings

logger = logging.getLogger(__name__)


class DataSyncService:
    """데이터 동기화 서비스"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.api_client = DataGoKrClient()
        self.preprocessor = DrugDataPreprocessor()
        self.embedding_service = get_embedding_service()

    async def sync_drugs(
        self,
        max_pages: int = 10,
        num_of_rows: int = 100,
        build_vectors: bool = True,
    ) -> dict:
        """공공데이터 API에서 의약품 데이터 동기화

        Args:
            max_pages: 수집할 최대 페이지 수
            num_of_rows: 페이지당 결과 수
            build_vectors: 벡터 인덱스도 함께 구축할지 여부

        Returns:
            동기화 결과 통계
        """
        stats = {
            "fetched": 0,
            "processed": 0,
            "saved": 0,
            "vectors_created": 0,
            "errors": 0,
        }

        try:
            # 1. API에서 데이터 수집
            logger.info(f"📥 API에서 데이터 수집 시작 (최대 {max_pages} 페이지)...")
            async with self.api_client as client:
                drugs = await client.collect_all_drugs(
                    max_pages=max_pages,
                    num_of_rows=num_of_rows,
                )
            stats["fetched"] = len(drugs)

            if not drugs:
                logger.warning("수집된 데이터가 없습니다.")
                return stats

            # 2. 데이터 전처리
            logger.info("🔄 데이터 전처리 중...")
            processed = self.preprocessor.preprocess_batch(drugs)
            stats["processed"] = len(processed)

            # 3. DB에 저장
            logger.info("💾 데이터베이스 저장 중...")
            saved_count = await self._save_drugs(processed)
            stats["saved"] = saved_count

            # 4. 벡터 인덱스 구축 (선택)
            if build_vectors:
                logger.info("🧠 벡터 인덱스 구축 중...")
                vector_count = await self._build_vectors(processed)
                stats["vectors_created"] = vector_count

            logger.info(f"✅ 동기화 완료: {stats}")
            return stats

        except Exception as e:
            logger.error(f"동기화 실패: {e}")
            stats["errors"] += 1
            raise

    async def _save_drugs(self, processed: List[dict]) -> int:
        """의약품 데이터를 DB에 저장 (upsert)"""
        saved_count = 0

        for item in processed:
            try:
                # 기존 데이터 확인
                existing = await self.session.execute(
                    select(Drug).where(Drug.id == item["id"])
                )
                drug = existing.scalar_one_or_none()

                if drug:
                    # 업데이트
                    for key, value in item.items():
                        if key != "document" and hasattr(drug, key):
                            setattr(drug, key, value)
                else:
                    # 새로 생성
                    drug = Drug(
                        id=item["id"],
                        item_name=item["item_name"],
                        entp_name=item["entp_name"],
                        efficacy=item["efficacy"],
                        use_method=item["use_method"],
                        warning_info=item["warning_info"],
                        caution_info=item["caution_info"],
                        interaction=item["interaction"],
                        side_effects=item["side_effects"],
                        storage_method=item["storage_method"],
                    )
                    self.session.add(drug)

                saved_count += 1

            except Exception as e:
                logger.warning(f"저장 실패: {item.get('item_name')} - {e}")
                continue

        await self.session.commit()
        return saved_count

    async def _build_vectors(self, processed: List[dict]) -> int:
        """벡터 인덱스 구축 (PGVector + Qdrant)"""
        vector_db = VectorDBService(self.session)

        # 기존 벡터 삭제
        await vector_db.delete_all()

        # 문서와 ID 추출
        documents = [item["document"] for item in processed]
        drug_ids = [item["id"] for item in processed]

        # 배치 임베딩 생성 (Dense)
        logger.info("🧠 Dense 임베딩 생성 중...")
        embeddings = await self.embedding_service.embed_batch(documents)

        # PGVector에 저장
        vectors = [
            {
                "drug_id": drug_id,
                "embedding": embedding,
                "document": document,
            }
            for drug_id, embedding, document in zip(drug_ids, embeddings, documents)
        ]
        pgvector_count = await vector_db.add_vectors_batch(vectors)

        # Qdrant + SPLADE 인덱싱 (활성화된 경우)
        if settings.ENABLE_QDRANT:
            await self._build_qdrant_vectors(processed, embeddings)

        return pgvector_count

    async def _build_qdrant_vectors(
        self,
        processed: List[dict],
        dense_embeddings: List[List[float]],
    ) -> int:
        """Qdrant 벡터 인덱스 구축 (Dense + Sparse)"""
        import gc
        try:
            qdrant_service = get_qdrant_service()
            splade_service = get_splade_service()

            # Qdrant 연결 확인
            if not qdrant_service._initialized:
                await qdrant_service.connect()
                await qdrant_service.create_collection(recreate=True)

            # SPLADE Sparse 임베딩 생성 (작은 배치로 메모리 절약)
            logger.info("🔧 SPLADE Sparse 임베딩 생성 중...")
            documents = [item["document"] for item in processed]
            sparse_embeddings = await splade_service.encode_batch(documents, batch_size=8)
            gc.collect()  # 메모리 정리

            # Qdrant 문서 준비
            qdrant_docs = [
                {
                    "drug_id": item["id"],
                    "item_name": item.get("item_name", ""),
                    "entp_name": item.get("entp_name", ""),
                    "efficacy": item.get("efficacy", ""),
                    "use_method": item.get("use_method", ""),
                    "caution_info": item.get("caution_info", ""),
                    "side_effects": item.get("side_effects", ""),
                }
                for item in processed
            ]

            # Qdrant에 업서트
            logger.info("📤 Qdrant에 벡터 업서트 중...")
            qdrant_count = await qdrant_service.upsert_documents(
                documents=qdrant_docs,
                dense_vectors=dense_embeddings,
                sparse_vectors=sparse_embeddings,
            )

            logger.info(f"✅ Qdrant 인덱싱 완료: {qdrant_count}개")
            return qdrant_count

        except Exception as e:
            logger.error(f"❌ Qdrant 인덱싱 실패: {e}")
            return 0

    async def rebuild_vectors(self) -> int:
        """기존 DB 데이터로 벡터 인덱스 재구축 (PGVector + Qdrant)"""
        vector_db = VectorDBService(self.session)

        # DB에서 모든 의약품 조회
        result = await self.session.execute(select(Drug))
        drugs = result.scalars().all()

        if not drugs:
            logger.warning("DB에 의약품 데이터가 없습니다.")
            return 0

        # 문서 생성 (Qdrant용 메타데이터 포함)
        processed = []
        for drug in drugs:
            document = self.preprocessor._create_document(
                drug.item_name,
                drug.entp_name or "",
                drug.efficacy or "",
                drug.use_method or "",
                drug.warning_info or "",
                drug.caution_info or "",
                drug.interaction or "",
                drug.side_effects or "",
                drug.storage_method or "",
            )
            processed.append({
                "id": drug.id,
                "document": document,
                "item_name": drug.item_name,
                "entp_name": drug.entp_name or "",
                "efficacy": drug.efficacy or "",
                "use_method": drug.use_method or "",
                "caution_info": drug.caution_info or "",
                "side_effects": drug.side_effects or "",
            })

        # 기존 벡터 삭제
        await vector_db.delete_all()

        # 임베딩 생성 및 저장
        documents = [item["document"] for item in processed]
        drug_ids = [item["id"] for item in processed]

        logger.info("🧠 Dense 임베딩 생성 중...")
        embeddings = await self.embedding_service.embed_batch(documents)

        vectors = [
            {
                "drug_id": drug_id,
                "embedding": embedding,
                "document": document,
            }
            for drug_id, embedding, document in zip(drug_ids, embeddings, documents)
        ]

        pgvector_count = await vector_db.add_vectors_batch(vectors)

        # Qdrant + SPLADE 인덱싱 (활성화된 경우)
        if settings.ENABLE_QDRANT:
            await self._build_qdrant_vectors(processed, embeddings)

        return pgvector_count
