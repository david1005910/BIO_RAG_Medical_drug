"""벡터 데이터베이스 서비스 - PGVector 연동"""
import logging
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.drug import DrugVector

logger = logging.getLogger(__name__)


class VectorDBService:
    """PGVector 기반 벡터 검색 서비스"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_vector(
        self,
        drug_id: str,
        embedding: List[float],
        document: str,
        chunk_index: int = 0,
    ) -> DrugVector:
        """단일 벡터 저장

        Args:
            drug_id: 의약품 ID
            embedding: 임베딩 벡터
            document: 원본 문서
            chunk_index: 청크 인덱스

        Returns:
            생성된 DrugVector 객체
        """
        vector = DrugVector(
            drug_id=drug_id,
            embedding=embedding,
            document=document,
            chunk_index=chunk_index,
        )
        self.session.add(vector)
        await self.session.commit()
        await self.session.refresh(vector)
        return vector

    async def add_vectors_batch(
        self,
        vectors: List[Dict],
    ) -> int:
        """벡터 배치 저장

        Args:
            vectors: [{"drug_id": str, "embedding": list, "document": str}]

        Returns:
            저장된 벡터 수
        """
        vector_objects = [
            DrugVector(
                drug_id=v["drug_id"],
                embedding=v["embedding"],
                document=v["document"],
                chunk_index=v.get("chunk_index", 0),
            )
            for v in vectors
        ]

        self.session.add_all(vector_objects)
        await self.session.commit()

        logger.info(f"✅ {len(vector_objects)}개 벡터 저장 완료")
        return len(vector_objects)

    async def search_similar(
        self,
        query_embedding: List[float],
        top_k: int = 5,
    ) -> List[Dict]:
        """코사인 유사도 기반 검색

        Args:
            query_embedding: 쿼리 임베딩 벡터
            top_k: 반환할 결과 수

        Returns:
            유사도 순으로 정렬된 결과 리스트
        """
        # 벡터를 PostgreSQL 형식으로 변환
        embedding_str = f"[{','.join(map(str, query_embedding))}]"

        # asyncpg에서 named parameters와 ::casting을 함께 사용할 때 문제가 있어서
        # 직접 문자열 포매팅 사용 (embedding은 float 배열이므로 SQL injection 위험 없음)
        query = text(f"""
            SELECT
                v.drug_id,
                v.document,
                d.item_name,
                d.entp_name,
                d.efficacy,
                d.use_method,
                d.caution_info,
                d.side_effects,
                1 - (v.embedding <=> '{embedding_str}'::vector) as similarity
            FROM drug_vectors v
            JOIN drugs d ON v.drug_id = d.id
            ORDER BY v.embedding <=> '{embedding_str}'::vector
            LIMIT :top_k
        """)

        result = await self.session.execute(
            query,
            {"top_k": top_k},
        )

        rows = result.fetchall()

        return [
            {
                "drug_id": row.drug_id,
                "document": row.document,
                "item_name": row.item_name,
                "entp_name": row.entp_name,
                "efficacy": row.efficacy,
                "use_method": row.use_method,
                "caution_info": row.caution_info,
                "side_effects": row.side_effects,
                "similarity": float(row.similarity) if row.similarity else 0.0,
            }
            for row in rows
        ]

    async def delete_by_drug_id(self, drug_id: str) -> int:
        """특정 의약품의 모든 벡터 삭제

        Args:
            drug_id: 의약품 ID

        Returns:
            삭제된 벡터 수
        """
        result = await self.session.execute(
            delete(DrugVector).where(DrugVector.drug_id == drug_id)
        )
        await self.session.commit()
        return result.rowcount

    async def delete_all(self) -> int:
        """모든 벡터 삭제 (주의해서 사용)

        Returns:
            삭제된 벡터 수
        """
        result = await self.session.execute(delete(DrugVector))
        await self.session.commit()
        logger.warning(f"⚠️ 모든 벡터 삭제됨: {result.rowcount}개")
        return result.rowcount

    async def get_vector_count(self) -> int:
        """저장된 벡터 총 수 조회"""
        result = await self.session.execute(
            text("SELECT COUNT(*) FROM drug_vectors")
        )
        return result.scalar() or 0

    async def get_drug_ids_with_vectors(self) -> List[str]:
        """벡터가 있는 의약품 ID 목록 조회"""
        result = await self.session.execute(
            text("SELECT DISTINCT drug_id FROM drug_vectors")
        )
        return [row[0] for row in result.fetchall()]
