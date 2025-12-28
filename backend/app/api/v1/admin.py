"""관리자 API 엔드포인트"""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.drug import Drug, DrugVector
from app.services.data_sync import DataSyncService
from app.services.vector_db import VectorDBService

router = APIRouter()


class SyncRequest(BaseModel):
    """데이터 동기화 요청"""

    max_pages: int = Field(default=10, ge=1, le=100, description="최대 페이지 수")
    build_vectors: bool = Field(default=True, description="벡터 인덱스 구축 여부")


class SyncResponse(BaseModel):
    """데이터 동기화 응답"""

    success: bool
    message: str
    stats: dict = {}


class StatsResponse(BaseModel):
    """시스템 통계 응답"""

    drugs_count: int
    vectors_count: int
    status: str = "healthy"


@router.post("/sync", response_model=SyncResponse)
async def sync_data(
    request: SyncRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db),
):
    """공공데이터 API에서 의약품 데이터 동기화

    ⚠️ 관리자 전용 API

    - **max_pages**: 수집할 최대 페이지 수 (1-100)
    - **build_vectors**: 벡터 인덱스도 함께 구축할지 여부
    """
    try:
        sync_service = DataSyncService(session)

        # 동기 실행 (소규모 데이터용)
        # 대규모 데이터는 background_tasks 사용 권장
        stats = await sync_service.sync_drugs(
            max_pages=request.max_pages,
            build_vectors=request.build_vectors,
        )

        return SyncResponse(
            success=True,
            message=f"동기화 완료: {stats['saved']}개 의약품, {stats['vectors_created']}개 벡터",
            stats=stats,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"동기화 실패: {str(e)}",
        )


@router.post("/rebuild-vectors", response_model=SyncResponse)
async def rebuild_vectors(
    session: AsyncSession = Depends(get_db),
):
    """벡터 인덱스 재구축

    기존 DB 데이터로 벡터 인덱스를 다시 구축합니다.
    """
    try:
        sync_service = DataSyncService(session)
        count = await sync_service.rebuild_vectors()

        return SyncResponse(
            success=True,
            message=f"벡터 인덱스 재구축 완료: {count}개",
            stats={"vectors_created": count},
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"재구축 실패: {str(e)}",
        )


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    session: AsyncSession = Depends(get_db),
):
    """시스템 통계 조회"""
    try:
        # 의약품 수
        drugs_result = await session.execute(select(func.count(Drug.id)))
        drugs_count = drugs_result.scalar() or 0

        # 벡터 수
        vectors_result = await session.execute(select(func.count(DrugVector.id)))
        vectors_count = vectors_result.scalar() or 0

        return StatsResponse(
            drugs_count=drugs_count,
            vectors_count=vectors_count,
            status="healthy",
        )

    except Exception as e:
        return StatsResponse(
            drugs_count=0,
            vectors_count=0,
            status=f"error: {str(e)}",
        )


@router.get("/health")
async def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "service": "medical-rag-api",
        "version": "1.0.0",
    }
