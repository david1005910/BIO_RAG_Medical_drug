"""검색 API 엔드포인트"""
import time
import random
import math
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.search import (
    SearchRequest,
    SearchResponse,
    SearchData,
    SearchMeta,
    DrugResult,
    DiseaseResult,
)
from app.services.rag_engine import RAGEngine
from app.models.search_log import SearchLog

router = APIRouter()


# Vector Visualization 스키마
class VectorPoint(BaseModel):
    """3D 공간의 벡터 포인트"""
    id: str
    name: str
    x: float
    y: float
    z: float
    similarity: float
    similarity_level: int  # 1-5 (1: 가장 유사, 5: 가장 덜 유사)
    color: str


class VectorVisualizationResponse(BaseModel):
    """벡터 시각화 응답"""
    success: bool
    query: str
    query_point: VectorPoint
    drug_points: List[VectorPoint]
    similarity_levels: List[dict]


def project_to_3d(similarity: float, index: int, total: int) -> tuple:
    """유사도를 기반으로 3D 좌표 생성

    유사도가 높을수록 중심(쿼리)에 가깝게 배치
    """
    # 유사도에 따른 거리 (0.0~1.0 -> 1.0~5.0)
    distance = 1.0 + (1.0 - similarity) * 4.0

    # 구 표면에 균등하게 분포 (피보나치 격자)
    golden_ratio = (1 + math.sqrt(5)) / 2
    theta = 2 * math.pi * index / golden_ratio
    phi = math.acos(1 - 2 * (index + 0.5) / total)

    x = distance * math.sin(phi) * math.cos(theta)
    y = distance * math.sin(phi) * math.sin(theta)
    z = distance * math.cos(phi)

    return x, y, z


def get_similarity_level(similarity: float) -> int:
    """유사도를 5단계로 분류"""
    if similarity >= 0.8:
        return 1  # 매우 높음
    elif similarity >= 0.6:
        return 2  # 높음
    elif similarity >= 0.4:
        return 3  # 중간
    elif similarity >= 0.2:
        return 4  # 낮음
    else:
        return 5  # 매우 낮음


def get_level_color(level: int) -> str:
    """유사도 레벨에 따른 색상"""
    colors = {
        1: "#22c55e",  # 초록 - 매우 높음
        2: "#84cc16",  # 라임 - 높음
        3: "#eab308",  # 노랑 - 중간
        4: "#f97316",  # 주황 - 낮음
        5: "#ef4444",  # 빨강 - 매우 낮음
    }
    return colors.get(level, "#6b7280")


@router.post("/search", response_model=SearchResponse)
async def search_drugs(
    request: SearchRequest,
    session: AsyncSession = Depends(get_db),
):
    """증상 기반 의약품 및 질병 검색

    사용자가 입력한 증상을 분석하여 관련 질병 정보와 의약품을 추천합니다.

    - **query**: 증상 설명 (예: "두통이 심하고 열이 나요")
    - **top_k**: 반환할 결과 수 (1-20, 기본값: 5)
    - **include_ai_response**: AI 설명 포함 여부 (기본값: true)
    - **include_diseases**: 질병 정보 포함 여부 (기본값: true)
    """
    start_time = time.time()

    try:
        rag_engine = RAGEngine(session=session)

        if request.include_ai_response:
            # 검색 + AI 응답 생성 (질병 정보 포함)
            response = await rag_engine.search_and_generate(
                query=request.query,
                top_k=request.top_k,
                include_diseases=request.include_diseases,
            )
            results = [
                DrugResult(
                    id=r.drug_id,
                    item_name=r.item_name,
                    entp_name=r.entp_name,
                    efficacy=r.efficacy,
                    use_method=r.use_method,
                    caution_info=r.caution_info,
                    side_effects=r.side_effects,
                    similarity=r.similarity,
                    relevance_score=r.relevance_score,
                )
                for r in response.results
            ]
            # 질병 결과 변환
            disease_results = None
            if response.disease_results:
                disease_results = [
                    DiseaseResult(
                        id=d.disease_id,
                        name=d.name,
                        name_en=d.name_en,
                        category=d.category,
                        description=d.description,
                        causes=d.causes,
                        symptoms=d.symptoms,
                        treatment=d.treatment,
                        prevention=d.prevention,
                        related_drugs=d.related_drugs,
                        similarity=d.similarity,
                        relevance_score=d.relevance_score,
                    )
                    for d in response.disease_results
                ]
            ai_response = response.ai_response
            disclaimer = response.disclaimer
        else:
            # 검색만
            search_results = await rag_engine.search(
                query=request.query,
                top_k=request.top_k,
            )
            results = [
                DrugResult(
                    id=r.drug_id,
                    item_name=r.item_name,
                    entp_name=r.entp_name,
                    efficacy=r.efficacy,
                    use_method=r.use_method,
                    caution_info=r.caution_info,
                    side_effects=r.side_effects,
                    similarity=r.similarity,
                    relevance_score=r.relevance_score,
                )
                for r in search_results
            ]
            disease_results = None
            ai_response = None
            disclaimer = "※ 이 정보는 참고용입니다. 실제 복약은 의사/약사와 상담하세요."

        response_time_ms = int((time.time() - start_time) * 1000)

        # 검색 로그 저장 (비동기, 실패해도 무시)
        try:
            log = SearchLog(
                query=request.query[:500],
                result_count=len(results),
                response_time_ms=response_time_ms,
            )
            session.add(log)
            await session.commit()
        except Exception:
            pass  # 로그 저장 실패는 무시

        return SearchResponse(
            success=True,
            data=SearchData(
                results=results,
                disease_results=disease_results,
                ai_response=ai_response,
                disclaimer=disclaimer,
            ),
            meta=SearchMeta(
                total_results=len(results),
                response_time_ms=response_time_ms,
                query=request.query,
            ),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"검색 중 오류가 발생했습니다: {str(e)}",
        )


@router.get("/vector-space", response_model=VectorVisualizationResponse)
async def get_vector_space(
    query: str,
    top_k: int = 20,
    session: AsyncSession = Depends(get_db),
):
    """검색어의 벡터 공간 시각화 데이터

    검색어와 관련 의약품들의 3D 벡터 공간 위치를 반환합니다.
    유사도에 따라 5단계로 분류하여 시각화에 사용할 수 있습니다.

    - **query**: 검색어
    - **top_k**: 반환할 의약품 수 (기본값: 20)
    """
    try:
        rag_engine = RAGEngine(session=session)

        # 검색 수행 (더 많은 결과를 가져와서 다양한 유사도 분포 확보)
        search_results = await rag_engine.search(
            query=query,
            top_k=min(top_k, 50),
            use_reranking=False,  # 원본 유사도 사용
        )

        # 쿼리 포인트 (중심)
        query_point = VectorPoint(
            id="query",
            name=query[:30] + "..." if len(query) > 30 else query,
            x=0.0,
            y=0.0,
            z=0.0,
            similarity=1.0,
            similarity_level=0,
            color="#a855f7",  # 보라색 (쿼리)
        )

        # 의약품 포인트들
        drug_points = []
        total = len(search_results)

        for i, result in enumerate(search_results):
            # 유사도 정규화 (0~1 범위로)
            similarity = min(max(result.similarity, 0.0), 1.0)

            # 3D 좌표 계산
            x, y, z = project_to_3d(similarity, i, total)

            # 유사도 레벨
            level = get_similarity_level(similarity)

            drug_points.append(VectorPoint(
                id=result.drug_id,
                name=result.item_name,
                x=x,
                y=y,
                z=z,
                similarity=round(similarity, 4),
                similarity_level=level,
                color=get_level_color(level),
            ))

        # 유사도 레벨 정보
        similarity_levels = [
            {"level": 1, "label": "매우 높음", "range": "80% 이상", "color": "#22c55e"},
            {"level": 2, "label": "높음", "range": "60-80%", "color": "#84cc16"},
            {"level": 3, "label": "중간", "range": "40-60%", "color": "#eab308"},
            {"level": 4, "label": "낮음", "range": "20-40%", "color": "#f97316"},
            {"level": 5, "label": "매우 낮음", "range": "20% 미만", "color": "#ef4444"},
        ]

        return VectorVisualizationResponse(
            success=True,
            query=query,
            query_point=query_point,
            drug_points=drug_points,
            similarity_levels=similarity_levels,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"벡터 시각화 데이터 생성 중 오류: {str(e)}",
        )
