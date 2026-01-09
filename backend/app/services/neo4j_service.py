"""Neo4j 그래프 서비스 - 노드 및 관계 관리"""
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.external.neo4j_client import Neo4jClient, get_neo4j_client

logger = logging.getLogger(__name__)


@dataclass
class GraphNode:
    """그래프 노드"""
    id: str
    label: str
    name: str
    properties: Dict[str, Any]


@dataclass
class GraphEdge:
    """그래프 엣지"""
    source: str
    target: str
    type: str
    properties: Dict[str, Any]


@dataclass
class GraphData:
    """시각화용 그래프 데이터"""
    nodes: List[GraphNode]
    edges: List[GraphEdge]


@dataclass
class DrugInteraction:
    """약물 상호작용 정보"""
    drug_id: str
    item_name: str
    interaction_type: str
    severity: int
    description: str


@dataclass
class RelatedDrug:
    """관련 약물 정보"""
    drug_id: str
    item_name: str
    relationship_type: str
    score: float


class Neo4jService:
    """Neo4j 그래프 서비스"""

    def __init__(self, client: Optional[Neo4jClient] = None):
        self.client = client or get_neo4j_client()

    def is_enabled(self) -> bool:
        """서비스 활성화 여부"""
        return self.client.is_enabled()

    # ==================== 노드 생성 ====================

    async def create_drug_node(
        self,
        drug_id: str,
        item_name: str,
        entp_name: Optional[str] = None,
        efficacy: Optional[str] = None,
        category: Optional[str] = None,
    ) -> bool:
        """Drug 노드 생성"""
        query = """
        MERGE (d:Drug {id: $drug_id})
        SET d.item_name = $item_name,
            d.entp_name = $entp_name,
            d.efficacy = $efficacy,
            d.category = $category,
            d.updated_at = datetime()
        ON CREATE SET d.created_at = datetime()
        RETURN d.id as id
        """
        result = await self.client.execute_write(
            query,
            {
                "drug_id": drug_id,
                "item_name": item_name,
                "entp_name": entp_name,
                "efficacy": efficacy,
                "category": category,
            },
        )
        return result.get("success", False)

    async def create_disease_node(
        self,
        disease_id: str,
        name: str,
        name_en: Optional[str] = None,
        category: Optional[str] = None,
    ) -> bool:
        """Disease 노드 생성"""
        query = """
        MERGE (d:Disease {id: $disease_id})
        SET d.name = $name,
            d.name_en = $name_en,
            d.category = $category,
            d.updated_at = datetime()
        ON CREATE SET d.created_at = datetime()
        RETURN d.id as id
        """
        result = await self.client.execute_write(
            query,
            {
                "disease_id": disease_id,
                "name": name,
                "name_en": name_en,
                "category": category,
            },
        )
        return result.get("success", False)

    async def create_symptom_node(self, symptom_name: str) -> bool:
        """Symptom 노드 생성"""
        normalized = symptom_name.strip().lower()
        query = """
        MERGE (s:Symptom {name: $name})
        SET s.normalized_name = $normalized,
            s.updated_at = datetime()
        ON CREATE SET s.created_at = datetime()
        RETURN s.name as name
        """
        result = await self.client.execute_write(
            query,
            {"name": symptom_name, "normalized": normalized},
        )
        return result.get("success", False)

    # ==================== 관계 생성 ====================

    async def create_interaction(
        self,
        drug_id_1: str,
        drug_id_2: str,
        interaction_type: str = "caution",
        severity: int = 2,
        description: Optional[str] = None,
    ) -> bool:
        """INTERACTS_WITH 관계 생성"""
        query = """
        MATCH (d1:Drug {id: $drug_id_1})
        MATCH (d2:Drug {id: $drug_id_2})
        MERGE (d1)-[r:INTERACTS_WITH]->(d2)
        SET r.interaction_type = $interaction_type,
            r.severity = $severity,
            r.description = $description,
            r.updated_at = datetime()
        ON CREATE SET r.created_at = datetime()
        RETURN type(r) as type
        """
        result = await self.client.execute_write(
            query,
            {
                "drug_id_1": drug_id_1,
                "drug_id_2": drug_id_2,
                "interaction_type": interaction_type,
                "severity": severity,
                "description": description,
            },
        )
        return result.get("success", False)

    async def create_treats_relationship(
        self,
        drug_id: str,
        disease_id: str,
        efficacy_level: str = "primary",
        evidence: Optional[str] = None,
    ) -> bool:
        """TREATS 관계 생성"""
        query = """
        MATCH (d:Drug {id: $drug_id})
        MATCH (dis:Disease {id: $disease_id})
        MERGE (d)-[r:TREATS]->(dis)
        SET r.efficacy_level = $efficacy_level,
            r.evidence = $evidence,
            r.updated_at = datetime()
        ON CREATE SET r.created_at = datetime()
        RETURN type(r) as type
        """
        result = await self.client.execute_write(
            query,
            {
                "drug_id": drug_id,
                "disease_id": disease_id,
                "efficacy_level": efficacy_level,
                "evidence": evidence,
            },
        )
        return result.get("success", False)

    async def create_relieves_relationship(
        self,
        drug_id: str,
        symptom_name: str,
        effectiveness: float = 0.5,
    ) -> bool:
        """RELIEVES 관계 생성"""
        query = """
        MATCH (d:Drug {id: $drug_id})
        MERGE (s:Symptom {name: $symptom_name})
        ON CREATE SET s.normalized_name = toLower($symptom_name), s.created_at = datetime()
        MERGE (d)-[r:RELIEVES]->(s)
        SET r.effectiveness = $effectiveness,
            r.updated_at = datetime()
        ON CREATE SET r.created_at = datetime()
        RETURN type(r) as type
        """
        result = await self.client.execute_write(
            query,
            {
                "drug_id": drug_id,
                "symptom_name": symptom_name,
                "effectiveness": effectiveness,
            },
        )
        return result.get("success", False)

    async def create_similar_to(
        self,
        drug_id_1: str,
        drug_id_2: str,
        similarity_score: float,
        similarity_type: str = "same_efficacy",
    ) -> bool:
        """SIMILAR_TO 관계 생성"""
        query = """
        MATCH (d1:Drug {id: $drug_id_1})
        MATCH (d2:Drug {id: $drug_id_2})
        MERGE (d1)-[r:SIMILAR_TO]->(d2)
        SET r.similarity_score = $similarity_score,
            r.similarity_type = $similarity_type,
            r.updated_at = datetime()
        ON CREATE SET r.created_at = datetime()
        RETURN type(r) as type
        """
        result = await self.client.execute_write(
            query,
            {
                "drug_id_1": drug_id_1,
                "drug_id_2": drug_id_2,
                "similarity_score": similarity_score,
                "similarity_type": similarity_type,
            },
        )
        return result.get("success", False)

    # ==================== 쿼리 ====================

    async def get_drug_interactions(
        self,
        drug_id: str,
        depth: int = 1,
    ) -> List[DrugInteraction]:
        """약물 상호작용 조회"""
        query = """
        MATCH (d:Drug {id: $drug_id})-[r:INTERACTS_WITH]-(other:Drug)
        RETURN other.id as drug_id,
               other.item_name as item_name,
               r.interaction_type as interaction_type,
               r.severity as severity,
               r.description as description
        ORDER BY r.severity DESC
        """
        results = await self.client.execute_query(query, {"drug_id": drug_id})
        return [
            DrugInteraction(
                drug_id=row["drug_id"],
                item_name=row["item_name"] or "",
                interaction_type=row["interaction_type"] or "unknown",
                severity=row["severity"] or 1,
                description=row["description"] or "",
            )
            for row in results
        ]

    async def get_related_drugs(
        self,
        drug_id: str,
        limit: int = 10,
    ) -> List[RelatedDrug]:
        """관련 약물 조회 (유사 약물 + 상호작용 약물)"""
        query = """
        MATCH (d:Drug {id: $drug_id})
        OPTIONAL MATCH (d)-[r1:SIMILAR_TO]-(similar:Drug)
        OPTIONAL MATCH (d)-[r2:INTERACTS_WITH]-(interacts:Drug)
        WITH d,
             collect(DISTINCT {
                drug_id: similar.id,
                item_name: similar.item_name,
                type: 'similar',
                score: r1.similarity_score
             }) as similar_drugs,
             collect(DISTINCT {
                drug_id: interacts.id,
                item_name: interacts.item_name,
                type: 'interacts',
                score: 1.0 - (r2.severity / 5.0)
             }) as interacting_drugs
        UNWIND similar_drugs + interacting_drugs as drug
        WITH drug WHERE drug.drug_id IS NOT NULL
        RETURN DISTINCT drug.drug_id as drug_id,
               drug.item_name as item_name,
               drug.type as relationship_type,
               drug.score as score
        ORDER BY drug.score DESC
        LIMIT $limit
        """
        results = await self.client.execute_query(
            query, {"drug_id": drug_id, "limit": limit}
        )
        return [
            RelatedDrug(
                drug_id=row["drug_id"],
                item_name=row["item_name"] or "",
                relationship_type=row["relationship_type"] or "unknown",
                score=row["score"] or 0.0,
            )
            for row in results
        ]

    async def get_drugs_for_disease(
        self,
        disease_id: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """질병 치료 약물 조회"""
        query = """
        MATCH (d:Drug)-[r:TREATS]->(dis:Disease {id: $disease_id})
        RETURN d.id as drug_id,
               d.item_name as item_name,
               d.entp_name as entp_name,
               r.efficacy_level as efficacy_level,
               r.evidence as evidence
        ORDER BY CASE r.efficacy_level
            WHEN 'primary' THEN 1
            WHEN 'secondary' THEN 2
            ELSE 3 END
        LIMIT $limit
        """
        return await self.client.execute_query(
            query, {"disease_id": disease_id, "limit": limit}
        )

    async def get_drugs_for_symptom(
        self,
        symptom: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """증상 완화 약물 조회"""
        query = """
        MATCH (d:Drug)-[r:RELIEVES]->(s:Symptom)
        WHERE s.name = $symptom OR s.normalized_name = toLower($symptom)
        RETURN d.id as drug_id,
               d.item_name as item_name,
               d.entp_name as entp_name,
               r.effectiveness as effectiveness
        ORDER BY r.effectiveness DESC
        LIMIT $limit
        """
        return await self.client.execute_query(
            query, {"symptom": symptom, "limit": limit}
        )

    async def get_drug_graph(
        self,
        drug_id: str,
        depth: int = 2,
    ) -> GraphData:
        """시각화용 약물 중심 그래프 데이터"""
        query = """
        MATCH path = (d:Drug {id: $drug_id})-[r*1..$depth]-(connected)
        WHERE connected:Drug OR connected:Disease OR connected:Symptom
        WITH nodes(path) as ns, relationships(path) as rs
        UNWIND ns as n
        WITH collect(DISTINCT n) as nodes, collect(DISTINCT rs) as all_rels
        UNWIND all_rels as rels
        UNWIND rels as r
        WITH nodes, collect(DISTINCT r) as relationships
        RETURN nodes, relationships
        """
        # depth를 쿼리에 직접 삽입 (파라미터로 전달 불가)
        query = query.replace("$depth", str(min(depth, 3)))

        results = await self.client.execute_query(query, {"drug_id": drug_id})

        nodes: List[GraphNode] = []
        edges: List[GraphEdge] = []
        seen_nodes = set()
        seen_edges = set()

        if results:
            for row in results:
                # 노드 처리
                for node in row.get("nodes", []):
                    node_id = node.get("id") or node.get("name")
                    if node_id and node_id not in seen_nodes:
                        labels = list(node.labels) if hasattr(node, "labels") else ["Unknown"]
                        nodes.append(
                            GraphNode(
                                id=node_id,
                                label=labels[0] if labels else "Unknown",
                                name=node.get("item_name") or node.get("name") or node_id,
                                properties=dict(node),
                            )
                        )
                        seen_nodes.add(node_id)

                # 관계 처리
                for rel in row.get("relationships", []):
                    start_id = rel.start_node.get("id") or rel.start_node.get("name")
                    end_id = rel.end_node.get("id") or rel.end_node.get("name")
                    edge_key = f"{start_id}-{rel.type}-{end_id}"

                    if edge_key not in seen_edges and start_id and end_id:
                        edges.append(
                            GraphEdge(
                                source=start_id,
                                target=end_id,
                                type=rel.type,
                                properties=dict(rel),
                            )
                        )
                        seen_edges.add(edge_key)

        return GraphData(nodes=nodes, edges=edges)

    async def get_cross_interactions(
        self,
        drug_ids: List[str],
    ) -> List[DrugInteraction]:
        """여러 약물 간 상호작용 조회"""
        if len(drug_ids) < 2:
            return []

        query = """
        MATCH (d1:Drug)-[r:INTERACTS_WITH]-(d2:Drug)
        WHERE d1.id IN $drug_ids AND d2.id IN $drug_ids AND d1.id < d2.id
        RETURN d1.id as drug_id_1,
               d1.item_name as item_name_1,
               d2.id as drug_id_2,
               d2.item_name as item_name_2,
               r.interaction_type as interaction_type,
               r.severity as severity,
               r.description as description
        ORDER BY r.severity DESC
        """
        results = await self.client.execute_query(query, {"drug_ids": drug_ids})

        interactions = []
        for row in results:
            interactions.append(
                DrugInteraction(
                    drug_id=row["drug_id_2"],
                    item_name=f"{row['item_name_1']} ↔ {row['item_name_2']}",
                    interaction_type=row["interaction_type"] or "unknown",
                    severity=row["severity"] or 1,
                    description=row["description"] or "",
                )
            )
        return interactions


# 싱글톤 인스턴스
_neo4j_service: Optional[Neo4jService] = None


def get_neo4j_service() -> Neo4jService:
    """Neo4j 서비스 싱글톤 반환"""
    global _neo4j_service
    if _neo4j_service is None:
        _neo4j_service = Neo4jService()
    return _neo4j_service
