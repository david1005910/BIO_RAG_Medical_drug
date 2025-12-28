"""Chat-related Pydantic schemas"""
from typing import Optional

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
    top_k: int = Field(default=5, ge=1, le=10, description="검색할 문서 수")


class ChatResponse(BaseModel):
    """Chat response schema"""

    success: bool = True
    message: str = Field(..., description="AI 응답 메시지")
    sources: list = Field(default=[], description="참조한 의약품 목록")
    disclaimer: str = Field(
        default="※ 이 정보는 참고용입니다. 실제 복약은 의사/약사와 상담하세요.",
        description="면책 조항",
    )
