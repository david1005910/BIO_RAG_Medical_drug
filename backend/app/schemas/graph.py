"""그래프 관련 Pydantic 스키마"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    """그래프 노드"""

    id: str = Field(..., description="노드 ID")
    label: str = Field(..., description="노드 레이블 (Drug, Disease, Symptom)")
    name: str = Field(..., description="노드 이름")
    properties: Dict[str, Any] = Field(default_factory=dict, description="추가 속성")


class GraphEdge(BaseModel):
    """그래프 엣지"""

    source: str = Field(..., description="시작 노드 ID")
    target: str = Field(..., description="끝 노드 ID")
    type: str = Field(..., description="관계 유형")
    properties: Dict[str, Any] = Field(default_factory=dict, description="관계 속성")


class GraphData(BaseModel):
    """시각화용 그래프 데이터"""

    nodes: List[GraphNode] = Field(default_factory=list, description="노드 목록")
    edges: List[GraphEdge] = Field(default_factory=list, description="엣지 목록")


class DrugInteractionResponse(BaseModel):
    """약물 상호작용 응답"""

    drug_id: str = Field(..., description="약물 ID")
    item_name: str = Field(..., description="약물명")
    interaction_type: str = Field(..., description="상호작용 유형 (contraindicated, caution, moderate)")
    severity: int = Field(..., ge=1, le=5, description="심각도 (1-5)")
    description: Optional[str] = Field(None, description="상호작용 설명")


class RelatedDrugResponse(BaseModel):
    """관련 약물 응답"""

    drug_id: str = Field(..., description="약물 ID")
    item_name: str = Field(..., description="약물명")
    relationship_type: str = Field(..., description="관계 유형 (similar, interacts)")
    score: float = Field(..., ge=0, le=1, description="관련도 점수")


class DiseasedrugResponse(BaseModel):
    """질병-약물 관계 응답"""

    drug_id: str = Field(..., description="약물 ID")
    item_name: str = Field(..., description="약물명")
    entp_name: Optional[str] = Field(None, description="제조사")
    efficacy_level: str = Field(..., description="효능 수준 (primary, secondary, off-label)")
    evidence: Optional[str] = Field(None, description="근거")


class SymptomDrugResponse(BaseModel):
    """증상-약물 관계 응답"""

    drug_id: str = Field(..., description="약물 ID")
    item_name: str = Field(..., description="약물명")
    entp_name: Optional[str] = Field(None, description="제조사")
    effectiveness: float = Field(..., ge=0, le=1, description="효과 점수")


class GraphInteractionsResponse(BaseModel):
    """약물 상호작용 API 응답"""

    success: bool = True
    drug_id: str = Field(..., description="조회한 약물 ID")
    interactions: List[DrugInteractionResponse] = Field(default_factory=list)
    total: int = Field(0, description="총 상호작용 수")


class GraphRelatedResponse(BaseModel):
    """관련 약물 API 응답"""

    success: bool = True
    drug_id: str = Field(..., description="조회한 약물 ID")
    related_drugs: List[RelatedDrugResponse] = Field(default_factory=list)
    total: int = Field(0, description="총 관련 약물 수")


class GraphVisualizationResponse(BaseModel):
    """그래프 시각화 API 응답"""

    success: bool = True
    drug_id: str = Field(..., description="중심 약물 ID")
    graph: GraphData = Field(..., description="그래프 데이터")
    depth: int = Field(2, description="탐색 깊이")


class DiseaseDrugsResponse(BaseModel):
    """질병 치료 약물 API 응답"""

    success: bool = True
    disease_id: str = Field(..., description="질병 ID")
    drugs: List[DiseasedrugResponse] = Field(default_factory=list)
    total: int = Field(0, description="총 약물 수")


class SymptomDrugsResponse(BaseModel):
    """증상 완화 약물 API 응답"""

    success: bool = True
    symptom: str = Field(..., description="증상명")
    drugs: List[SymptomDrugResponse] = Field(default_factory=list)
    total: int = Field(0, description="총 약물 수")


class GraphStatsResponse(BaseModel):
    """그래프 통계 응답"""

    success: bool = True
    stats: Dict[str, int] = Field(default_factory=dict, description="통계 데이터")
