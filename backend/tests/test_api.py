"""API endpoint tests"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """헬스 체크 API 테스트"""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """루트 엔드포인트 테스트"""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data


@pytest.mark.asyncio
async def test_drugs_list_empty(client: AsyncClient):
    """빈 의약품 목록 조회 테스트"""
    response = await client.get("/api/v1/drugs")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"] == []
    assert data["meta"]["total_items"] == 0


@pytest.mark.asyncio
async def test_drug_detail_not_found(client: AsyncClient):
    """존재하지 않는 의약품 조회 테스트"""
    response = await client.get("/api/v1/drugs/nonexistent123")
    assert response.status_code == 404
