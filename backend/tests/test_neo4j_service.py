"""Neo4j 서비스 테스트"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.neo4j_service import (
    Neo4jService,
    DrugInteraction,
    RelatedDrug,
    GraphData,
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
