"""검색 API 엔드포인트"""
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
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
