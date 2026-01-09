"""Neo4j 그래프 데이터베이스 클라이언트"""
import logging
from typing import Any, Dict, List, Optional

from neo4j import AsyncDriver, AsyncGraphDatabase
from neo4j.exceptions import AuthError, ServiceUnavailable

from app.core.config import settings

logger = logging.getLogger(__name__)


class Neo4jClient:
    """Neo4j 비동기 클라이언트"""

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
    ):
        self.uri = uri or settings.NEO4J_URI
        self.user = user or settings.NEO4J_USER
        self.password = password or settings.NEO4J_PASSWORD
        self.database = database or settings.NEO4J_DATABASE
        self._driver: Optional[AsyncDriver] = None
        self._connected = False

    async def connect(self) -> bool:
        """Neo4j 연결"""
        if not settings.ENABLE_NEO4J:
            logger.info("Neo4j가 비활성화되어 있습니다")
            return False

        if not self.password:
            logger.warning("NEO4J_PASSWORD가 설정되지 않았습니다")
            return False

        try:
            self._driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
            )
            # 연결 테스트
            async with self._driver.session(database=self.database) as session:
                await session.run("RETURN 1")
            self._connected = True
            logger.info(f"🔗 Neo4j 연결 성공: {self.uri}")
            return True
        except AuthError as e:
            logger.error(f"Neo4j 인증 실패: {e}")
            return False
        except ServiceUnavailable as e:
            logger.error(f"Neo4j 서비스 연결 실패: {e}")
            return False
        except Exception as e:
            logger.error(f"Neo4j 연결 오류: {e}")
            return False

    async def close(self):
        """연결 종료"""
        if self._driver:
            await self._driver.close()
            self._connected = False
            logger.info("Neo4j 연결 종료")

    def is_connected(self) -> bool:
        """연결 상태 확인"""
        return self._connected

    def is_enabled(self) -> bool:
        """Neo4j 활성화 여부"""
        return settings.ENABLE_NEO4J and self._connected

    async def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """읽기 쿼리 실행"""
        if not self.is_enabled():
            return []

        try:
            async with self._driver.session(database=self.database) as session:
                result = await session.run(query, parameters or {})
                records = await result.data()
                return records
        except Exception as e:
            logger.error(f"Neo4j 쿼리 실행 오류: {e}")
            return []

    async def execute_write(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """쓰기 쿼리 실행"""
        if not self.is_enabled():
            return {"success": False, "error": "Neo4j not connected"}

        try:
            async with self._driver.session(database=self.database) as session:
                result = await session.run(query, parameters or {})
                summary = await result.consume()
                return {
                    "success": True,
                    "nodes_created": summary.counters.nodes_created,
                    "nodes_deleted": summary.counters.nodes_deleted,
                    "relationships_created": summary.counters.relationships_created,
                    "relationships_deleted": summary.counters.relationships_deleted,
                    "properties_set": summary.counters.properties_set,
                }
        except Exception as e:
            logger.error(f"Neo4j 쓰기 오류: {e}")
            return {"success": False, "error": str(e)}

    async def create_constraints_and_indexes(self) -> bool:
        """제약조건 및 인덱스 생성"""
        if not self.is_enabled():
            return False

        constraints = [
            "CREATE CONSTRAINT drug_id IF NOT EXISTS FOR (d:Drug) REQUIRE d.id IS UNIQUE",
            "CREATE CONSTRAINT disease_id IF NOT EXISTS FOR (d:Disease) REQUIRE d.id IS UNIQUE",
            "CREATE CONSTRAINT symptom_name IF NOT EXISTS FOR (s:Symptom) REQUIRE s.name IS UNIQUE",
        ]

        indexes = [
            "CREATE INDEX drug_name IF NOT EXISTS FOR (d:Drug) ON (d.item_name)",
            "CREATE INDEX disease_name IF NOT EXISTS FOR (d:Disease) ON (d.name)",
        ]

        try:
            for query in constraints + indexes:
                await self.execute_write(query)
            logger.info("✅ Neo4j 제약조건 및 인덱스 생성 완료")
            return True
        except Exception as e:
            logger.error(f"Neo4j 스키마 생성 오류: {e}")
            return False

    async def get_stats(self) -> Dict[str, int]:
        """그래프 통계 조회"""
        if not self.is_enabled():
            return {}

        stats_query = """
        CALL {
            MATCH (d:Drug) RETURN 'drugs' as label, count(d) as count
            UNION ALL
            MATCH (d:Disease) RETURN 'diseases' as label, count(d) as count
            UNION ALL
            MATCH (s:Symptom) RETURN 'symptoms' as label, count(s) as count
            UNION ALL
            MATCH ()-[r:INTERACTS_WITH]->() RETURN 'interactions' as label, count(r) as count
            UNION ALL
            MATCH ()-[r:TREATS]->() RETURN 'treats' as label, count(r) as count
            UNION ALL
            MATCH ()-[r:RELIEVES]->() RETURN 'relieves' as label, count(r) as count
            UNION ALL
            MATCH ()-[r:SIMILAR_TO]->() RETURN 'similar_to' as label, count(r) as count
        }
        RETURN label, count
        """
        results = await self.execute_query(stats_query)
        return {row["label"]: row["count"] for row in results}


# 싱글톤 인스턴스
_neo4j_client: Optional[Neo4jClient] = None


def get_neo4j_client() -> Neo4jClient:
    """Neo4j 클라이언트 싱글톤 반환"""
    global _neo4j_client
    if _neo4j_client is None:
        _neo4j_client = Neo4jClient()
    return _neo4j_client


async def initialize_neo4j() -> bool:
    """Neo4j 초기화 (앱 시작 시 호출)"""
    client = get_neo4j_client()
    connected = await client.connect()
    if connected:
        await client.create_constraints_and_indexes()
    return connected


async def close_neo4j():
    """Neo4j 연결 종료 (앱 종료 시 호출)"""
    global _neo4j_client
    if _neo4j_client:
        await _neo4j_client.close()
        _neo4j_client = None
