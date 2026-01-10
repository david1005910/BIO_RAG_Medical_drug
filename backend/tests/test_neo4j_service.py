"""Neo4j 서비스 테스트"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.neo4j_service import (
    DrugInteraction,
    GraphData,
    GraphEdge,
    GraphNode,
    Neo4jService,
    RelatedDrug,
    get_neo4j_service,
)


class TestNeo4jService:
    """Neo4j 서비스 단위 테스트"""

    @pytest.fixture
    def mock_client(self):
        """Mock Neo4j 클라이언트"""
        client = MagicMock()
        client.is_enabled.return_value = True
        client.execute_query = AsyncMock(return_value=[])
        client.execute_write = AsyncMock(return_value={"success": True})
        return client

    @pytest.fixture
    def service(self, mock_client):
        """테스트용 Neo4j 서비스"""
        return Neo4jService(client=mock_client)

    @pytest.mark.asyncio
    async def test_create_drug_node(self, service, mock_client):
        """Drug 노드 생성 테스트"""
        result = await service.create_drug_node(
            drug_id="12345",
            item_name="타이레놀정",
            entp_name="테스트제약",
            efficacy="두통, 발열 완화",
        )

        assert result is True
        mock_client.execute_write.assert_called_once()
        call_args = mock_client.execute_write.call_args
        assert "MERGE (d:Drug {id: $drug_id})" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_create_disease_node(self, service, mock_client):
        """Disease 노드 생성 테스트"""
        result = await service.create_disease_node(
            disease_id="D001",
            name="감기",
            category="호흡기",
        )

        assert result is True
        mock_client.execute_write.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_symptom_node(self, service, mock_client):
        """Symptom 노드 생성 테스트"""
        result = await service.create_symptom_node("두통")

        assert result is True
        mock_client.execute_write.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_interaction(self, service, mock_client):
        """INTERACTS_WITH 관계 생성 테스트"""
        result = await service.create_interaction(
            drug_id_1="12345",
            drug_id_2="67890",
            interaction_type="caution",
            severity=3,
            description="함께 복용 주의",
        )

        assert result is True
        mock_client.execute_write.assert_called_once()
        call_args = mock_client.execute_write.call_args
        assert "INTERACTS_WITH" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_create_treats_relationship(self, service, mock_client):
        """TREATS 관계 생성 테스트"""
        result = await service.create_treats_relationship(
            drug_id="12345",
            disease_id="D001",
            efficacy_level="primary",
        )

        assert result is True
        mock_client.execute_write.assert_called_once()
        call_args = mock_client.execute_write.call_args
        assert "TREATS" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_create_relieves_relationship(self, service, mock_client):
        """RELIEVES 관계 생성 테스트"""
        result = await service.create_relieves_relationship(
            drug_id="12345",
            symptom_name="두통",
            effectiveness=0.8,
        )

        assert result is True
        mock_client.execute_write.assert_called_once()
        call_args = mock_client.execute_write.call_args
        assert "RELIEVES" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_create_similar_to(self, service, mock_client):
        """SIMILAR_TO 관계 생성 테스트"""
        result = await service.create_similar_to(
            drug_id_1="12345",
            drug_id_2="67890",
            similarity_score=0.85,
            similarity_type="same_efficacy",
        )

        assert result is True
        mock_client.execute_write.assert_called_once()
        call_args = mock_client.execute_write.call_args
        assert "SIMILAR_TO" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_drug_interactions(self, service, mock_client):
        """약물 상호작용 조회 테스트"""
        mock_client.execute_query.return_value = [
            {
                "drug_id": "67890",
                "item_name": "게보린정",
                "interaction_type": "caution",
                "severity": 3,
                "description": "함께 복용 주의",
            }
        ]

        interactions = await service.get_drug_interactions("12345")

        assert len(interactions) == 1
        assert interactions[0].drug_id == "67890"
        assert interactions[0].item_name == "게보린정"
        assert interactions[0].severity == 3

    @pytest.mark.asyncio
    async def test_get_related_drugs(self, service, mock_client):
        """관련 약물 조회 테스트"""
        mock_client.execute_query.return_value = [
            {
                "drug_id": "67890",
                "item_name": "게보린정",
                "relationship_type": "similar",
                "score": 0.85,
            }
        ]

        related = await service.get_related_drugs("12345", limit=10)

        assert len(related) == 1
        assert related[0].drug_id == "67890"
        assert related[0].score == 0.85

    @pytest.mark.asyncio
    async def test_get_drugs_for_disease(self, service, mock_client):
        """질병 치료 약물 조회 테스트"""
        mock_client.execute_query.return_value = [
            {
                "drug_id": "12345",
                "item_name": "타이레놀정",
                "entp_name": "테스트제약",
                "efficacy_level": "primary",
                "evidence": "test",
            }
        ]

        drugs = await service.get_drugs_for_disease("D001")

        assert len(drugs) == 1
        assert drugs[0]["drug_id"] == "12345"

    @pytest.mark.asyncio
    async def test_get_drugs_for_symptom(self, service, mock_client):
        """증상 완화 약물 조회 테스트"""
        mock_client.execute_query.return_value = [
            {
                "drug_id": "12345",
                "item_name": "타이레놀정",
                "entp_name": "테스트제약",
                "effectiveness": 0.8,
            }
        ]

        drugs = await service.get_drugs_for_symptom("두통")

        assert len(drugs) == 1
        assert drugs[0]["drug_id"] == "12345"

    @pytest.mark.asyncio
    async def test_service_disabled(self, mock_client):
        """서비스 비활성화 시 테스트"""
        mock_client.is_enabled.return_value = False
        service = Neo4jService(client=mock_client)

        # 비활성화 상태에서는 빈 결과 반환
        interactions = await service.get_drug_interactions("12345")
        assert interactions == []

    @pytest.mark.asyncio
    async def test_get_cross_interactions(self, service, mock_client):
        """여러 약물 간 상호작용 조회 테스트"""
        mock_client.execute_query.return_value = [
            {
                "drug_id_1": "12345",
                "item_name_1": "타이레놀정",
                "drug_id_2": "67890",
                "item_name_2": "게보린정",
                "interaction_type": "caution",
                "severity": 3,
                "description": "함께 복용 주의",
            }
        ]

        interactions = await service.get_cross_interactions(["12345", "67890", "11111"])

        assert len(interactions) == 1
        assert "타이레놀정" in interactions[0].item_name
        assert "게보린정" in interactions[0].item_name

    @pytest.mark.asyncio
    async def test_get_cross_interactions_single_drug(self, service, mock_client):
        """단일 약물로 상호작용 조회 시 빈 결과 반환"""
        interactions = await service.get_cross_interactions(["12345"])

        assert interactions == []
        # execute_query가 호출되지 않아야 함
        mock_client.execute_query.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_cross_interactions_empty_list(self, service, mock_client):
        """빈 리스트로 상호작용 조회 시 빈 결과 반환"""
        interactions = await service.get_cross_interactions([])

        assert interactions == []
        mock_client.execute_query.assert_not_called()

    def test_is_enabled(self, service, mock_client):
        """서비스 활성화 상태 확인"""
        mock_client.is_enabled.return_value = True
        assert service.is_enabled() is True

        mock_client.is_enabled.return_value = False
        assert service.is_enabled() is False

    @pytest.mark.asyncio
    async def test_get_drug_graph_empty_results(self, service, mock_client):
        """빈 그래프 결과 테스트"""
        mock_client.execute_query.return_value = []

        graph = await service.get_drug_graph("12345", depth=2)

        assert isinstance(graph, GraphData)
        assert graph.nodes == []
        assert graph.edges == []

    @pytest.mark.asyncio
    async def test_get_drug_graph_with_nodes_and_edges(self, service, mock_client):
        """노드와 엣지가 있는 그래프 테스트"""
        # Mock 노드 객체 생성
        mock_drug_node = MagicMock()
        mock_drug_node.get.side_effect = lambda k, d=None: {
            "id": "12345",
            "item_name": "타이레놀정",
            "name": None,
        }.get(k, d)
        mock_drug_node.labels = ["Drug"]
        mock_drug_node.__iter__ = lambda self: iter(
            [("id", "12345"), ("item_name", "타이레놀정")]
        )

        mock_symptom_node = MagicMock()
        mock_symptom_node.get.side_effect = lambda k, d=None: {
            "id": None,
            "name": "두통",
            "item_name": None,
        }.get(k, d)
        mock_symptom_node.labels = ["Symptom"]
        mock_symptom_node.__iter__ = lambda self: iter([("name", "두통")])

        # Mock 관계 객체 생성
        mock_rel = MagicMock()
        mock_rel.type = "RELIEVES"
        mock_rel.start_node = MagicMock()
        mock_rel.start_node.get.side_effect = lambda k, d=None: {
            "id": "12345",
            "name": None,
        }.get(k, d)
        mock_rel.end_node = MagicMock()
        mock_rel.end_node.get.side_effect = lambda k, d=None: {
            "id": None,
            "name": "두통",
        }.get(k, d)
        mock_rel.__iter__ = lambda self: iter([("effectiveness", 0.8)])

        mock_client.execute_query.return_value = [
            {
                "nodes": [mock_drug_node, mock_symptom_node],
                "relationships": [mock_rel],
            }
        ]

        graph = await service.get_drug_graph("12345", depth=2)

        assert isinstance(graph, GraphData)
        assert len(graph.nodes) == 2
        assert len(graph.edges) == 1

        # 노드 확인
        node_ids = [n.id for n in graph.nodes]
        assert "12345" in node_ids
        assert "두통" in node_ids

        # 엣지 확인
        assert graph.edges[0].type == "RELIEVES"
        assert graph.edges[0].source == "12345"
        assert graph.edges[0].target == "두통"

    @pytest.mark.asyncio
    async def test_get_drug_graph_depth_limit(self, service, mock_client):
        """그래프 깊이 제한 테스트 (최대 3)"""
        mock_client.execute_query.return_value = []

        await service.get_drug_graph("12345", depth=5)

        # depth가 3으로 제한되어야 함
        call_args = mock_client.execute_query.call_args
        query = call_args[0][0]
        assert "*1..3" in query  # depth가 3으로 제한됨

    @pytest.mark.asyncio
    async def test_get_drug_graph_duplicate_nodes_filtered(self, service, mock_client):
        """중복 노드 필터링 테스트"""
        mock_node = MagicMock()
        mock_node.get.side_effect = lambda k, d=None: {
            "id": "12345",
            "item_name": "타이레놀정",
        }.get(k, d)
        mock_node.labels = ["Drug"]
        mock_node.__iter__ = lambda self: iter([("id", "12345")])

        # 동일한 노드가 두 번 반환됨
        mock_client.execute_query.return_value = [
            {"nodes": [mock_node, mock_node], "relationships": []},
        ]

        graph = await service.get_drug_graph("12345")

        # 중복이 제거되어 하나만 있어야 함
        assert len(graph.nodes) == 1

    @pytest.mark.asyncio
    async def test_get_drug_interactions_with_null_values(self, service, mock_client):
        """NULL 값이 있는 상호작용 조회 테스트"""
        mock_client.execute_query.return_value = [
            {
                "drug_id": "67890",
                "item_name": None,
                "interaction_type": None,
                "severity": None,
                "description": None,
            }
        ]

        interactions = await service.get_drug_interactions("12345")

        assert len(interactions) == 1
        assert interactions[0].item_name == ""
        assert interactions[0].interaction_type == "unknown"
        assert interactions[0].severity == 1
        assert interactions[0].description == ""

    @pytest.mark.asyncio
    async def test_get_related_drugs_with_null_values(self, service, mock_client):
        """NULL 값이 있는 관련 약물 조회 테스트"""
        mock_client.execute_query.return_value = [
            {
                "drug_id": "67890",
                "item_name": None,
                "relationship_type": None,
                "score": None,
            }
        ]

        related = await service.get_related_drugs("12345")

        assert len(related) == 1
        assert related[0].item_name == ""
        assert related[0].relationship_type == "unknown"
        assert related[0].score == 0.0

    @pytest.mark.asyncio
    async def test_get_cross_interactions_with_null_values(self, service, mock_client):
        """NULL 값이 있는 교차 상호작용 조회 테스트"""
        mock_client.execute_query.return_value = [
            {
                "drug_id_1": "12345",
                "item_name_1": "약품1",
                "drug_id_2": "67890",
                "item_name_2": "약품2",
                "interaction_type": None,
                "severity": None,
                "description": None,
            }
        ]

        interactions = await service.get_cross_interactions(["12345", "67890"])

        assert len(interactions) == 1
        assert interactions[0].interaction_type == "unknown"
        assert interactions[0].severity == 1
        assert interactions[0].description == ""


class TestDataClasses:
    """데이터 클래스 테스트"""

    def test_graph_node_creation(self):
        """GraphNode 생성 테스트"""
        node = GraphNode(
            id="12345",
            label="Drug",
            name="타이레놀정",
            properties={"efficacy": "두통 완화"},
        )

        assert node.id == "12345"
        assert node.label == "Drug"
        assert node.name == "타이레놀정"
        assert node.properties["efficacy"] == "두통 완화"

    def test_graph_edge_creation(self):
        """GraphEdge 생성 테스트"""
        edge = GraphEdge(
            source="12345",
            target="두통",
            type="RELIEVES",
            properties={"effectiveness": 0.8},
        )

        assert edge.source == "12345"
        assert edge.target == "두통"
        assert edge.type == "RELIEVES"
        assert edge.properties["effectiveness"] == 0.8

    def test_graph_data_creation(self):
        """GraphData 생성 테스트"""
        nodes = [
            GraphNode(id="1", label="Drug", name="약품1", properties={}),
            GraphNode(id="2", label="Symptom", name="두통", properties={}),
        ]
        edges = [
            GraphEdge(source="1", target="2", type="RELIEVES", properties={}),
        ]

        graph = GraphData(nodes=nodes, edges=edges)

        assert len(graph.nodes) == 2
        assert len(graph.edges) == 1

    def test_drug_interaction_creation(self):
        """DrugInteraction 생성 테스트"""
        interaction = DrugInteraction(
            drug_id="12345",
            item_name="타이레놀정",
            interaction_type="caution",
            severity=3,
            description="주의 필요",
        )

        assert interaction.drug_id == "12345"
        assert interaction.item_name == "타이레놀정"
        assert interaction.severity == 3

    def test_related_drug_creation(self):
        """RelatedDrug 생성 테스트"""
        related = RelatedDrug(
            drug_id="12345",
            item_name="타이레놀정",
            relationship_type="similar",
            score=0.85,
        )

        assert related.drug_id == "12345"
        assert related.relationship_type == "similar"
        assert related.score == 0.85


class TestGetNeo4jService:
    """get_neo4j_service 싱글톤 테스트"""

    def teardown_method(self):
        """테스트 후 싱글톤 초기화"""
        import app.services.neo4j_service as neo4j_module

        neo4j_module._neo4j_service = None

    @patch("app.services.neo4j_service.get_neo4j_client")
    def test_get_neo4j_service_creates_singleton(self, mock_get_client):
        """싱글톤 생성 테스트"""
        import app.services.neo4j_service as neo4j_module

        neo4j_module._neo4j_service = None

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        service1 = get_neo4j_service()
        service2 = get_neo4j_service()

        assert service1 is service2
        # 클라이언트는 한 번만 생성되어야 함
        assert mock_get_client.call_count == 1

    @patch("app.services.neo4j_service.get_neo4j_client")
    def test_get_neo4j_service_returns_neo4j_service(self, mock_get_client):
        """Neo4jService 인스턴스 반환 테스트"""
        import app.services.neo4j_service as neo4j_module

        neo4j_module._neo4j_service = None

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        service = get_neo4j_service()

        assert isinstance(service, Neo4jService)
