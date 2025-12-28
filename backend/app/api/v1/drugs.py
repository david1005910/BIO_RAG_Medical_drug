"""의약품 API 엔드포인트"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.drug import Drug
from app.schemas.drug import DrugDetail, DrugResponse
from app.schemas.response import PaginatedResponse, PaginationMeta

router = APIRouter()


@router.get("/drugs/{drug_id}", response_model=DrugDetail)
async def get_drug_detail(
    drug_id: str,
    session: AsyncSession = Depends(get_db),
):
    """의약품 상세 정보 조회

    - **drug_id**: 품목기준코드 (itemSeq)
    """
    result = await session.execute(select(Drug).where(Drug.id == drug_id))
    drug = result.scalar_one_or_none()

    if not drug:
        raise HTTPException(status_code=404, detail="의약품을 찾을 수 없습니다.")

    return DrugDetail.model_validate(drug)


@router.get("/drugs", response_model=PaginatedResponse[DrugResponse])
async def get_drugs_list(
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(20, ge=1, le=100, description="페이지 크기"),
    search: Optional[str] = Query(None, description="의약품명 검색"),
    session: AsyncSession = Depends(get_db),
):
    """의약품 목록 조회 (페이지네이션)

    - **page**: 페이지 번호 (1부터 시작)
    - **page_size**: 페이지당 결과 수 (최대 100)
    - **search**: 의약품명 검색어 (선택)
    """
    # 기본 쿼리
    query = select(Drug)

    # 검색 필터
    if search:
        query = query.where(Drug.item_name.ilike(f"%{search}%"))

    # 전체 개수 조회
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total_items = total_result.scalar() or 0

    # 페이지네이션
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(Drug.item_name)

    result = await session.execute(query)
    drugs = result.scalars().all()

    # 응답 구성
    total_pages = (total_items + page_size - 1) // page_size

    return PaginatedResponse(
        success=True,
        data=[DrugResponse.model_validate(drug) for drug in drugs],
        meta=PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
        ),
    )
