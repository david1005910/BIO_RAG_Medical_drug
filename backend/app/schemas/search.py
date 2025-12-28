"""Search-related Pydantic schemas"""
from typing import List, Optional

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Search request schema"""

    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="검색할 증상",
        examples=["두통이 심하고 열이 나요"],
    )
    top_k: int = Field(default=5, ge=1, le=20, description="반환할 결과 수")
    include_ai_response: bool = Field(default=True, description="AI 응답 포함 여부")
    include_diseases: bool = Field(default=True, description="질병 정보 포함 여부")


class DrugResult(BaseModel):
    """Individual drug result in search response"""

    id: str = Field(..., description="품목기준코드")
    item_name: str = Field(..., description="제품명")
    entp_name: Optional[str] = Field(None, description="제조사")
    efficacy: Optional[str] = Field(None, description="효능효과")
    use_method: Optional[str] = Field(None, description="용법용량")
    caution_info: Optional[str] = Field(None, description="주의사항")
    side_effects: Optional[str] = Field(None, description="부작용")
    similarity: float = Field(..., ge=0, le=1, description="벡터 유사도 점수")
    relevance_score: Optional[float] = Field(None, ge=0, le=1, description="Cohere Reranking 관련성 점수")


class DiseaseResult(BaseModel):
    """Individual disease result in search response"""

    id: str = Field(..., description="질병 코드")
    name: str = Field(..., description="질병명")
    name_en: Optional[str] = Field(None, description="영문명")
    category: Optional[str] = Field(None, description="분류")
    description: Optional[str] = Field(None, description="질병 설명")
    causes: Optional[str] = Field(None, description="원인")
    symptoms: Optional[str] = Field(None, description="증상")
    treatment: Optional[str] = Field(None, description="치료 방법")
    prevention: Optional[str] = Field(None, description="예방법")
    related_drugs: Optional[str] = Field(None, description="관련 의약품")
    similarity: float = Field(..., ge=0, le=1, description="벡터 유사도 점수")
    relevance_score: Optional[float] = Field(None, ge=0, le=1, description="Cohere Reranking 관련성 점수")


class SearchData(BaseModel):
    """Search response data"""

    results: List[DrugResult]
    disease_results: Optional[List[DiseaseResult]] = Field(None, description="질병 검색 결과")
    ai_response: Optional[str] = Field(None, description="AI 생성 응답")
    disclaimer: str = Field(
        default="※ 이 정보는 참고용입니다. 실제 복약은 의사/약사와 상담하세요.",
        description="면책 조항",
    )


class SearchMeta(BaseModel):
    """Search response metadata"""

    total_results: int
    response_time_ms: int
    query: str


class SearchResponse(BaseModel):
    """Full search response schema"""

    success: bool = True
    data: SearchData
    meta: SearchMeta
