"""대화형 RAG API 엔드포인트"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.rag_engine import RAGEngine

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat_with_rag(
    request: ChatRequest,
    session: AsyncSession = Depends(get_db),
):
    """대화형 의약품 상담

    자연어로 의약품에 대해 질문하면 AI가 답변합니다.

    - **message**: 질문 메시지 (예: "두통이 심한데 어떤 약을 먹으면 좋을까요?")
    - **top_k**: 참조할 문서 수 (1-10, 기본값: 5)
    """
    try:
        rag_engine = RAGEngine(session=session)

        # RAG 검색 및 응답 생성
        response = await rag_engine.search_and_generate(
            query=request.message,
            top_k=request.top_k,
        )

        # 참조 의약품 목록
        sources = [
            {
                "id": r.drug_id,
                "name": r.item_name,
                "similarity": round(r.similarity, 2),
            }
            for r in response.results
        ]

        return ChatResponse(
            success=True,
            message=response.ai_response or "응답을 생성할 수 없습니다.",
            sources=sources,
            disclaimer=response.disclaimer,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"대화 처리 중 오류가 발생했습니다: {str(e)}",
        )
