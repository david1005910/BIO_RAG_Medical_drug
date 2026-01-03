"""Chat-related Pydantic schemas"""
from typing import List, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Chat request schema for conversational RAG"""

    message: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="사용자 메시지",
        examples=["두통이 심한데 어떤 약을 먹으면 좋을까요?"],
    )
    session_id: Optional[str] = Field(
        default=None,
        description="세션 ID (메모리 기능 활성화 시 필요)",
        examples=["user-123-session-456"],
    )
    top_k: int = Field(default=5, ge=1, le=10, description="검색할 문서 수")
    use_memory: bool = Field(default=True, description="메모리 기능 사용 여부")


class ChatResponse(BaseModel):
    """Chat response schema"""

    success: bool = True
    message: str = Field(..., description="AI 응답 메시지")
    sources: list = Field(default=[], description="참조한 의약품 목록")
    disclaimer: str = Field(
        default="※ 이 정보는 참고용입니다. 실제 복약은 의사/약사와 상담하세요.",
        description="면책 조항",
    )
    session_id: Optional[str] = Field(default=None, description="세션 ID")
    from_cache: bool = Field(default=False, description="캐시된 응답 여부")
    conversation_turn: int = Field(default=1, description="대화 턴 번호")


class ConversationHistoryItem(BaseModel):
    """대화 히스토리 항목"""

    query: str = Field(..., description="사용자 질문")
    response: str = Field(..., description="AI 응답")
    timestamp: str = Field(..., description="응답 시간")


class ConversationHistoryResponse(BaseModel):
    """대화 히스토리 응답"""

    success: bool = True
    session_id: str = Field(..., description="세션 ID")
    history: List[ConversationHistoryItem] = Field(default=[], description="대화 히스토리")
    total_turns: int = Field(default=0, description="총 대화 수")


class ClearHistoryResponse(BaseModel):
    """히스토리 삭제 응답"""

    success: bool = True
    session_id: str = Field(..., description="세션 ID")
    message: str = Field(default="대화 히스토리가 삭제되었습니다.")
