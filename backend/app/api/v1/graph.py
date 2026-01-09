"""그래프 API 엔드포인트"""
import logging

from fastapi import APIRouter, HTTPException, Query

from app.external.neo4j_client import get_neo4j_client
from app.schemas.graph import (
    DiseasedrugResponse,
    DiseaseDrugsResponse,
    DrugInteractionResponse,
    GraphData,
    GraphEdge,
    GraphInteractionsResponse,
    GraphNode,
    GraphRelatedResponse,
    GraphStatsResponse,
    GraphVisualizationResponse,
    RelatedDrugResponse,
    SymptomDrugResponse,
    SymptomDrugsResponse,
)
from app.services.neo4j_service import get_neo4j_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/graph", tags=["그래프"])


@router.get("/health")
async def graph_health():
    """그래프 DB 헬스 체크"""
    client = get_neo4j_client()
    return {
        "enabled": client.is_enabled(),
        "connected": client.is_connected(),
    }


@router.get("/stats", response_model=GraphStatsResponse)
async def get_graph_stats():
    """그래프 통계 조회"""
    client = get_neo4j_client()
    if not client.is_enabled():
        return GraphStatsResponse(success=False, stats={})

    stats = await client.get_stats()
    return GraphStatsResponse(success=True, stats=stats)


@router.get("/drug/{drug_id}/interactions", response_model=GraphInteractionsResponse)
async def get_drug_interactions(
    drug_id: str,
    depth: int = Query(1, ge=1, le=3, description="탐색 깊이"),
):
    """약물 상호작용 조회

    - **drug_id**: 약물 ID (품목기준코드)
    - **depth**: 탐색 깊이 (1-3)
    """
    service = get_neo4j_service()
    if not service.is_enabled():
        raise HTTPException(status_code=503, detail="Neo4j 서비스가 비활성화되어 있습니다")

    interactions = await service.get_drug_interactions(drug_id, depth)

    return GraphInteractionsResponse(
        success=True,
        drug_id=drug_id,
        interactions=[
            DrugInteractionResponse(
                drug_id=i.drug_id,
                item_name=i.item_name,
                interaction_type=i.interaction_type,
                severity=i.severity,
                description=i.description,
            )
            for i in interactions
        ],
        total=len(interactions),
    )


@router.get("/drug/{drug_id}/related", response_model=GraphRelatedResponse)
async def get_related_drugs(
    drug_id: str,
    limit: int = Query(10, ge=1, le=50, description="최대 결과 수"),
):
    """관련 약물 조회 (유사 약물 + 상호작용 약물)

    - **drug_id**: 약물 ID (품목기준코드)
    - **limit**: 최대 결과 수
    """
    service = get_neo4j_service()
    if not service.is_enabled():
        raise HTTPException(status_code=503, detail="Neo4j 서비스가 비활성화되어 있습니다")

    related = await service.get_related_drugs(drug_id, limit)

    return GraphRelatedResponse(
        success=True,
        drug_id=drug_id,
        related_drugs=[
            RelatedDrugResponse(
                drug_id=r.drug_id,
                item_name=r.item_name,
                relationship_type=r.relationship_type,
                score=r.score,
            )
            for r in related
        ],
        total=len(related),
    )


@router.get("/drug/{drug_id}/graph", response_model=GraphVisualizationResponse)
async def get_drug_graph(
    drug_id: str,
    depth: int = Query(2, ge=1, le=3, description="탐색 깊이"),
):
    """시각화용 약물 중심 그래프 데이터

    - **drug_id**: 약물 ID (품목기준코드)
    - **depth**: 탐색 깊이 (1-3)
    """
    service = get_neo4j_service()
    if not service.is_enabled():
        raise HTTPException(status_code=503, detail="Neo4j 서비스가 비활성화되어 있습니다")

    graph_data = await service.get_drug_graph(drug_id, depth)

    return GraphVisualizationResponse(
        success=True,
        drug_id=drug_id,
        graph=GraphData(
            nodes=[
                GraphNode(
                    id=n.id,
                    label=n.label,
                    name=n.name,
                    properties=n.properties,
                )
                for n in graph_data.nodes
            ],
            edges=[
                GraphEdge(
                    source=e.source,
                    target=e.target,
                    type=e.type,
                    properties=e.properties,
                )
                for e in graph_data.edges
            ],
        ),
        depth=depth,
    )


@router.get("/disease/{disease_id}/drugs", response_model=DiseaseDrugsResponse)
async def get_drugs_for_disease(
    disease_id: str,
    limit: int = Query(20, ge=1, le=100, description="최대 결과 수"),
):
    """질병 치료 약물 조회

    - **disease_id**: 질병 ID
    - **limit**: 최대 결과 수
    """
    service = get_neo4j_service()
    if not service.is_enabled():
        raise HTTPException(status_code=503, detail="Neo4j 서비스가 비활성화되어 있습니다")

    drugs = await service.get_drugs_for_disease(disease_id, limit)

    return DiseaseDrugsResponse(
        success=True,
        disease_id=disease_id,
        drugs=[
            DiseasedrugResponse(
                drug_id=d["drug_id"],
                item_name=d["item_name"] or "",
                entp_name=d.get("entp_name"),
                efficacy_level=d.get("efficacy_level", "unknown"),
                evidence=d.get("evidence"),
            )
            for d in drugs
        ],
        total=len(drugs),
    )


@router.get("/symptom/{symptom}/drugs", response_model=SymptomDrugsResponse)
async def get_drugs_for_symptom(
    symptom: str,
    limit: int = Query(20, ge=1, le=100, description="최대 결과 수"),
):
    """증상 완화 약물 조회

    - **symptom**: 증상명 (예: 두통, 발열)
    - **limit**: 최대 결과 수
    """
    service = get_neo4j_service()
    if not service.is_enabled():
        raise HTTPException(status_code=503, detail="Neo4j 서비스가 비활성화되어 있습니다")

    drugs = await service.get_drugs_for_symptom(symptom, limit)

    return SymptomDrugsResponse(
        success=True,
        symptom=symptom,
        drugs=[
            SymptomDrugResponse(
                drug_id=d["drug_id"],
                item_name=d["item_name"] or "",
                entp_name=d.get("entp_name"),
                effectiveness=d.get("effectiveness", 0.5),
            )
            for d in drugs
        ],
        total=len(drugs),
    )
