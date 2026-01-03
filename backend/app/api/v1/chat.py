"""대화형 RAG API 엔드포인트 (메모리 기능 포함)"""
import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationHistoryResponse,
    ConversationHistoryItem,
    ClearHistoryResponse,
)
from app.services.rag_engine import RAGEngine
from app.services.memory_service import get_memory_service, MemoryService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_memory() -> MemoryService:
    """메모리 서비스 의존성"""
    return get_memory_service()


@router.post("/chat", response_model=ChatResponse)
async def chat_with_rag(
    request: ChatRequest,
    session: AsyncSession = Depends(get_db),
    memory: MemoryService = Depends(get_memory),
):
    """대화형 의약품 상담 (메모리 기능 포함)

    자연어로 의약품에 대해 질문하면 AI가 답변합니다.
    세션 ID를 제공하면 이전 대화를 참조하여 답변합니다.

    - **message**: 질문 메시지 (예: "두통이 심한데 어떤 약을 먹으면 좋을까요?")
    - **session_id**: 세션 ID (선택, 메모리 기능 사용 시)
    - **top_k**: 참조할 문서 수 (1-10, 기본값: 5)
    - **use_memory**: 메모리 기능 사용 여부 (기본값: true)
    """
    try:
        # 세션 ID 생성 또는 사용
        session_id = request.session_id or str(uuid.uuid4())
        use_memory = request.use_memory and memory.is_enabled()

        # 1. 캐시 확인 (중복 검색 방지)
        if use_memory:
            cached = await memory.get_cached_response(request.message)
            if cached:
                # 히스토리에도 추가
                await memory.add_to_history(
                    session_id=session_id,
                    query=request.message,
                    response=cached.response,
                    sources=cached.sources,
                )
                history_length = len(await memory.get_history(session_id))

                return ChatResponse(
                    success=True,
                    message=cached.response,
                    sources=cached.sources,
                    session_id=session_id,
                    from_cache=True,
                    conversation_turn=history_length,
                )

        # 2. 이전 대화 컨텍스트 가져오기
        previous_context = ""
        history_length = 0
        if use_memory:
            previous_context = await memory.get_recent_context(session_id, limit=3)
            history = await memory.get_history(session_id)
            history_length = len(history)

        # 3. RAG 검색 및 응답 생성
        rag_engine = RAGEngine(session=session)

        # 이전 대화가 있으면 쿼리에 컨텍스트 추가
        enhanced_query = request.message
        if previous_context:
            logger.info(f"📚 이전 대화 참조: {history_length}개 턴")

        response = await rag_engine.search_and_generate(
            query=enhanced_query,
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

        ai_response = response.ai_response or "응답을 생성할 수 없습니다."

        # 4. 메모리에 저장
        if use_memory:
            # 응답 캐싱
            await memory.cache_response(
                query=request.message,
                response=ai_response,
                sources=sources,
            )
            # 히스토리에 추가
            await memory.add_to_history(
                session_id=session_id,
                query=request.message,
                response=ai_response,
                sources=sources,
            )
            history_length += 1

        return ChatResponse(
            success=True,
            message=ai_response,
            sources=sources,
            disclaimer=response.disclaimer,
            session_id=session_id,
            from_cache=False,
            conversation_turn=history_length,
        )

    except Exception as e:
        logger.error(f"대화 처리 오류: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"대화 처리 중 오류가 발생했습니다: {str(e)}",
        )


@router.get("/chat/history/{session_id}", response_model=ConversationHistoryResponse)
async def get_conversation_history(
    session_id: str,
    limit: int = 20,
    memory: MemoryService = Depends(get_memory),
):
    """대화 히스토리 조회

    - **session_id**: 세션 ID
    - **limit**: 최대 조회 수 (기본값: 20)
    """
    if not memory.is_enabled():
        raise HTTPException(status_code=503, detail="메모리 서비스가 비활성화되어 있습니다")

    history = await memory.get_history(session_id, limit=limit)

    return ConversationHistoryResponse(
        success=True,
        session_id=session_id,
        history=[
            ConversationHistoryItem(
                query=turn.query,
                response=turn.response,
                timestamp=turn.timestamp,
            )
            for turn in history
        ],
        total_turns=len(history),
    )


@router.delete("/chat/history/{session_id}", response_model=ClearHistoryResponse)
async def clear_conversation_history(
    session_id: str,
    memory: MemoryService = Depends(get_memory),
):
    """대화 히스토리 삭제

    - **session_id**: 세션 ID
    """
    if not memory.is_enabled():
        raise HTTPException(status_code=503, detail="메모리 서비스가 비활성화되어 있습니다")

    success = await memory.clear_history(session_id)

    if success:
        return ClearHistoryResponse(
            success=True,
            session_id=session_id,
            message="대화 히스토리가 삭제되었습니다.",
        )
    else:
        raise HTTPException(status_code=500, detail="히스토리 삭제에 실패했습니다")


@router.get("/chat/memory/status")
async def get_memory_status(
    memory: MemoryService = Depends(get_memory),
):
    """메모리 서비스 상태 확인"""
    stats = await memory.get_stats()
    return {
        "success": True,
        "memory_enabled": memory.is_enabled(),
        "stats": stats,
    }
