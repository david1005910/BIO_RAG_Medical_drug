"""질병 벡터 데이터베이스 서비스 - PGVector 연동"""
import logging
from typing import Dict, List

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class DiseaseVectorDBService:
    """PGVector 기반 질병 벡터 검색 서비스"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def search_similar(
        self,
        query_embedding: List[float],
        top_k: int = 3,
    ) -> List[Dict]:
        """코사인 유사도 기반 질병 검색

        Args:
            query_embedding: 쿼리 임베딩 벡터
            top_k: 반환할 결과 수

        Returns:
            유사도 순으로 정렬된 질병 결과 리스트
        """
        # 벡터를 PostgreSQL 형식으로 변환
        embedding_str = f"[{','.join(map(str, query_embedding))}]"

        query = text(f"""
            SELECT
                v.disease_id,
                v.document,
                v.chunk_type,
                d.name,
                d.name_en,
                d.category,
                d.description,
                d.causes,
                d.symptoms,
                d.diagnosis,
                d.treatment,
                d.prevention,
                d.related_drugs,
                1 - (v.embedding <=> '{embedding_str}'::vector) as similarity
            FROM disease_vectors v
            JOIN diseases d ON v.disease_id = d.id
            ORDER BY v.embedding <=> '{embedding_str}'::vector
            LIMIT :top_k
        """)

        result = await self.session.execute(
            query,
            {"top_k": top_k},
        )

        rows = result.fetchall()

        # 질병 ID별로 중복 제거 (가장 높은 유사도만 유지)
        seen_diseases = set()
        unique_results = []

        for row in rows:
            if row.disease_id not in seen_diseases:
                seen_diseases.add(row.disease_id)
                unique_results.append({
                    "disease_id": row.disease_id,
                    "document": row.document,
                    "chunk_type": row.chunk_type,
                    "name": row.name,
                    "name_en": row.name_en,
                    "category": row.category,
                    "description": row.description,
                    "causes": row.causes,
                    "symptoms": row.symptoms,
                    "diagnosis": row.diagnosis,
                    "treatment": row.treatment,
                    "prevention": row.prevention,
                    "related_drugs": row.related_drugs,
                    "similarity": float(row.similarity) if row.similarity else 0.0,
                })

        return unique_results

    async def get_vector_count(self) -> int:
        """저장된 질병 벡터 총 수 조회"""
        result = await self.session.execute(
            text("SELECT COUNT(*) FROM disease_vectors")
        )
        return result.scalar() or 0

    async def get_disease_count(self) -> int:
        """저장된 질병 총 수 조회"""
        result = await self.session.execute(
            text("SELECT COUNT(*) FROM diseases")
        )
        return result.scalar() or 0
