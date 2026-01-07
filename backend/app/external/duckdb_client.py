"""DuckDB 클라이언트 - 경량 메모리/파일 기반 저장소

Redis 대안으로 사용 가능한 DuckDB 기반 메모리 클라이언트.
파일 기반으로 영속성을 제공하면서도 Redis와 유사한 인터페이스 제공.
"""
import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

import duckdb

from app.core.config import settings
from app.external.base_memory_client import BaseMemoryClient

logger = logging.getLogger(__name__)


class DuckDBClient(BaseMemoryClient):
    """DuckDB 기반 메모리 클라이언트 - BaseMemoryClient 구현

    Redis와 동일한 인터페이스를 제공하며, 파일 기반 영속성 지원.
    동기 API를 비동기로 래핑하여 사용.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.DUCKDB_PATH
        self._conn: Optional[duckdb.DuckDBPyConnection] = None
        self._enabled = False
        self._lock = asyncio.Lock()

    @property
    def is_enabled(self) -> bool:
        """DuckDB 활성화 여부"""
        return self._enabled and self._conn is not None

    async def connect(self) -> bool:
        """DuckDB 연결 및 테이블 초기화"""
        try:
            # 디렉토리 생성
            db_dir = os.path.dirname(self.db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)

            # DuckDB 연결 (비동기 래핑)
            loop = asyncio.get_event_loop()
            self._conn = await loop.run_in_executor(
                None, lambda: duckdb.connect(self.db_path)
            )

            # 테이블 초기화
            await self._init_tables()

            self._enabled = True
            logger.info(f"✅ DuckDB 연결 성공: {self.db_path}")
            return True
        except Exception as e:
            logger.error(f"❌ DuckDB 연결 실패: {e}")
            self._enabled = False
            return False

    async def _init_tables(self) -> None:
        """내부 테이블 초기화"""
        loop = asyncio.get_event_loop()

        def create_tables():
            # Key-Value 저장소
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS kv_store (
                    key VARCHAR PRIMARY KEY,
                    value TEXT NOT NULL,
                    expires_at DOUBLE,
                    created_at DOUBLE DEFAULT (epoch(now()))
                )
            """)

            # 리스트 저장소 (Redis 리스트 시뮬레이션)
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS list_store (
                    key VARCHAR NOT NULL,
                    idx INTEGER NOT NULL,
                    value TEXT NOT NULL,
                    created_at DOUBLE DEFAULT (epoch(now())),
                    PRIMARY KEY (key, idx)
                )
            """)

            # 인덱스 생성
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_kv_expires
                ON kv_store(expires_at)
            """)
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_list_key
                ON list_store(key)
            """)

        await loop.run_in_executor(None, create_tables)

    async def close(self) -> None:
        """DuckDB 연결 종료"""
        if self._conn:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._conn.close)
            self._conn = None
            logger.info("👋 DuckDB 연결 종료")

    async def _cleanup_expired(self) -> None:
        """만료된 키 정리"""
        if not self.is_enabled:
            return
        try:
            current_time = time.time()
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._conn.execute(
                    "DELETE FROM kv_store WHERE expires_at IS NOT NULL AND expires_at < ?",
                    [current_time]
                )
            )
        except Exception as e:
            logger.error(f"DuckDB 만료 키 정리 오류: {e}")

    # ==================== 기본 연산 ====================

    async def get(self, key: str) -> Optional[str]:
        """값 조회"""
        if not self.is_enabled:
            return None
        try:
            await self._cleanup_expired()
            current_time = time.time()
            loop = asyncio.get_event_loop()

            result = await loop.run_in_executor(
                None,
                lambda: self._conn.execute(
                    """SELECT value FROM kv_store
                    WHERE key = ? AND (expires_at IS NULL OR expires_at > ?)""",
                    [key, current_time]
                ).fetchone()
            )
            return result[0] if result else None
        except Exception as e:
            logger.error(f"DuckDB GET 오류: {e}")
            return None

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """값 저장"""
        if not self.is_enabled:
            return False
        try:
            expires_at = time.time() + ttl if ttl else None
            loop = asyncio.get_event_loop()

            async with self._lock:
                await loop.run_in_executor(
                    None,
                    lambda: self._conn.execute(
                        """INSERT OR REPLACE INTO kv_store (key, value, expires_at)
                        VALUES (?, ?, ?)""",
                        [key, value, expires_at]
                    )
                )
            return True
        except Exception as e:
            logger.error(f"DuckDB SET 오류: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """키 삭제"""
        if not self.is_enabled:
            return False
        try:
            loop = asyncio.get_event_loop()
            async with self._lock:
                await loop.run_in_executor(
                    None,
                    lambda: self._conn.execute(
                        "DELETE FROM kv_store WHERE key = ?", [key]
                    )
                )
                # 리스트도 삭제
                await loop.run_in_executor(
                    None,
                    lambda: self._conn.execute(
                        "DELETE FROM list_store WHERE key = ?", [key]
                    )
                )
            return True
        except Exception as e:
            logger.error(f"DuckDB DELETE 오류: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """키 존재 여부 확인"""
        if not self.is_enabled:
            return False
        try:
            current_time = time.time()
            loop = asyncio.get_event_loop()

            # KV 스토어에서 확인
            result = await loop.run_in_executor(
                None,
                lambda: self._conn.execute(
                    """SELECT 1 FROM kv_store
                    WHERE key = ? AND (expires_at IS NULL OR expires_at > ?)
                    UNION
                    SELECT 1 FROM list_store WHERE key = ?
                    LIMIT 1""",
                    [key, current_time, key]
                ).fetchone()
            )
            return result is not None
        except Exception as e:
            logger.error(f"DuckDB EXISTS 오류: {e}")
            return False

    # ==================== JSON 연산 ====================

    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """JSON 값 조회"""
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None

    async def set_json(self, key: str, data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """JSON 값 저장"""
        try:
            json_str = json.dumps(data, ensure_ascii=False)
            return await self.set(key, json_str, ttl)
        except Exception as e:
            logger.error(f"DuckDB SET_JSON 오류: {e}")
            return False

    # ==================== 리스트 연산 ====================

    async def rpush(self, key: str, value: str) -> bool:
        """리스트 끝에 값 추가"""
        if not self.is_enabled:
            return False
        try:
            loop = asyncio.get_event_loop()
            async with self._lock:
                # 현재 최대 인덱스 조회
                max_idx = await loop.run_in_executor(
                    None,
                    lambda: self._conn.execute(
                        "SELECT COALESCE(MAX(idx), -1) FROM list_store WHERE key = ?",
                        [key]
                    ).fetchone()[0]
                )
                # 새 항목 추가
                await loop.run_in_executor(
                    None,
                    lambda: self._conn.execute(
                        "INSERT INTO list_store (key, idx, value) VALUES (?, ?, ?)",
                        [key, max_idx + 1, value]
                    )
                )
            return True
        except Exception as e:
            logger.error(f"DuckDB RPUSH 오류: {e}")
            return False

    async def lpush(self, key: str, value: str) -> bool:
        """리스트 앞에 값 추가"""
        if not self.is_enabled:
            return False
        try:
            loop = asyncio.get_event_loop()
            async with self._lock:
                # 모든 인덱스 +1
                await loop.run_in_executor(
                    None,
                    lambda: self._conn.execute(
                        "UPDATE list_store SET idx = idx + 1 WHERE key = ?",
                        [key]
                    )
                )
                # 새 항목을 인덱스 0에 추가
                await loop.run_in_executor(
                    None,
                    lambda: self._conn.execute(
                        "INSERT INTO list_store (key, idx, value) VALUES (?, 0, ?)",
                        [key, value]
                    )
                )
            return True
        except Exception as e:
            logger.error(f"DuckDB LPUSH 오류: {e}")
            return False

    async def lrange(self, key: str, start: int, end: int) -> List[str]:
        """리스트 범위 조회"""
        if not self.is_enabled:
            return []
        try:
            loop = asyncio.get_event_loop()

            # end가 -1이면 끝까지
            if end == -1:
                result = await loop.run_in_executor(
                    None,
                    lambda: self._conn.execute(
                        """SELECT value FROM list_store
                        WHERE key = ? AND idx >= ?
                        ORDER BY idx""",
                        [key, start]
                    ).fetchall()
                )
            else:
                result = await loop.run_in_executor(
                    None,
                    lambda: self._conn.execute(
                        """SELECT value FROM list_store
                        WHERE key = ? AND idx >= ? AND idx <= ?
                        ORDER BY idx""",
                        [key, start, end]
                    ).fetchall()
                )
            return [row[0] for row in result]
        except Exception as e:
            logger.error(f"DuckDB LRANGE 오류: {e}")
            return []

    async def llen(self, key: str) -> int:
        """리스트 길이"""
        if not self.is_enabled:
            return 0
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self._conn.execute(
                    "SELECT COUNT(*) FROM list_store WHERE key = ?",
                    [key]
                ).fetchone()
            )
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"DuckDB LLEN 오류: {e}")
            return 0

    async def ltrim(self, key: str, start: int, end: int) -> bool:
        """리스트 트리밍 (범위 외 삭제)"""
        if not self.is_enabled:
            return False
        try:
            loop = asyncio.get_event_loop()
            async with self._lock:
                if end == -1:
                    # end가 -1이면 start 이전만 삭제
                    await loop.run_in_executor(
                        None,
                        lambda: self._conn.execute(
                            "DELETE FROM list_store WHERE key = ? AND idx < ?",
                            [key, start]
                        )
                    )
                else:
                    await loop.run_in_executor(
                        None,
                        lambda: self._conn.execute(
                            "DELETE FROM list_store WHERE key = ? AND (idx < ? OR idx > ?)",
                            [key, start, end]
                        )
                    )
                # 인덱스 재정렬
                await self._reindex_list(key)
            return True
        except Exception as e:
            logger.error(f"DuckDB LTRIM 오류: {e}")
            return False

    async def _reindex_list(self, key: str) -> None:
        """리스트 인덱스 재정렬"""
        loop = asyncio.get_event_loop()

        # 모든 값을 가져와서 재인덱싱
        rows = await loop.run_in_executor(
            None,
            lambda: self._conn.execute(
                "SELECT value FROM list_store WHERE key = ? ORDER BY idx",
                [key]
            ).fetchall()
        )

        # 삭제 후 재삽입
        await loop.run_in_executor(
            None,
            lambda: self._conn.execute(
                "DELETE FROM list_store WHERE key = ?", [key]
            )
        )

        for idx, (value,) in enumerate(rows):
            await loop.run_in_executor(
                None,
                lambda i=idx, v=value: self._conn.execute(
                    "INSERT INTO list_store (key, idx, value) VALUES (?, ?, ?)",
                    [key, i, v]
                )
            )

    # ==================== TTL 연산 ====================

    async def expire(self, key: str, seconds: int) -> bool:
        """키 만료 시간 설정"""
        if not self.is_enabled:
            return False
        try:
            expires_at = time.time() + seconds
            loop = asyncio.get_event_loop()
            async with self._lock:
                await loop.run_in_executor(
                    None,
                    lambda: self._conn.execute(
                        "UPDATE kv_store SET expires_at = ? WHERE key = ?",
                        [expires_at, key]
                    )
                )
            return True
        except Exception as e:
            logger.error(f"DuckDB EXPIRE 오류: {e}")
            return False

    async def ttl(self, key: str) -> int:
        """키 남은 TTL 조회 (-1: 만료 없음, -2: 키 없음)"""
        if not self.is_enabled:
            return -2
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self._conn.execute(
                    "SELECT expires_at FROM kv_store WHERE key = ?",
                    [key]
                ).fetchone()
            )

            if not result:
                return -2  # 키 없음

            expires_at = result[0]
            if expires_at is None:
                return -1  # 만료 없음

            remaining = int(expires_at - time.time())
            return max(remaining, 0)
        except Exception as e:
            logger.error(f"DuckDB TTL 오류: {e}")
            return -2

    # ==================== 증감 연산 ====================

    async def incr(self, key: str) -> int:
        """정수 값 증가"""
        if not self.is_enabled:
            return 0
        try:
            loop = asyncio.get_event_loop()
            async with self._lock:
                # 현재 값 조회
                current = await self.get(key)
                if current is None:
                    new_value = 1
                else:
                    new_value = int(current) + 1

                await loop.run_in_executor(
                    None,
                    lambda: self._conn.execute(
                        """INSERT OR REPLACE INTO kv_store (key, value, expires_at)
                        VALUES (?, ?, (SELECT expires_at FROM kv_store WHERE key = ?))""",
                        [key, str(new_value), key]
                    )
                )
            return new_value
        except Exception as e:
            logger.error(f"DuckDB INCR 오류: {e}")
            return 0

    # ==================== 유틸리티 ====================

    async def keys(self, pattern: str) -> List[str]:
        """패턴 매칭 키 조회 (SQL LIKE 패턴 사용)"""
        if not self.is_enabled:
            return []
        try:
            # Redis 패턴 (*) -> SQL LIKE 패턴 (%)
            sql_pattern = pattern.replace("*", "%")
            current_time = time.time()
            loop = asyncio.get_event_loop()

            result = await loop.run_in_executor(
                None,
                lambda: self._conn.execute(
                    """SELECT DISTINCT key FROM (
                        SELECT key FROM kv_store
                        WHERE key LIKE ? AND (expires_at IS NULL OR expires_at > ?)
                        UNION
                        SELECT key FROM list_store WHERE key LIKE ?
                    )""",
                    [sql_pattern, current_time, sql_pattern]
                ).fetchall()
            )
            return [row[0] for row in result]
        except Exception as e:
            logger.error(f"DuckDB KEYS 오류: {e}")
            return []

    async def flush_all(self) -> bool:
        """모든 데이터 삭제 (주의: 전체 삭제)"""
        if not self.is_enabled:
            return False
        try:
            loop = asyncio.get_event_loop()
            async with self._lock:
                await loop.run_in_executor(
                    None,
                    lambda: self._conn.execute("DELETE FROM kv_store")
                )
                await loop.run_in_executor(
                    None,
                    lambda: self._conn.execute("DELETE FROM list_store")
                )
            logger.warning("⚠️ DuckDB 전체 데이터 삭제됨")
            return True
        except Exception as e:
            logger.error(f"DuckDB FLUSHALL 오류: {e}")
            return False


# 싱글톤 인스턴스
_duckdb_client: Optional[DuckDBClient] = None


def get_duckdb_client() -> DuckDBClient:
    """DuckDB 클라이언트 싱글톤 반환"""
    global _duckdb_client
    if _duckdb_client is None:
        _duckdb_client = DuckDBClient()
    return _duckdb_client


async def initialize_duckdb() -> bool:
    """DuckDB 초기화"""
    client = get_duckdb_client()
    return await client.connect()


async def close_duckdb():
    """DuckDB 종료"""
    global _duckdb_client
    if _duckdb_client:
        await _duckdb_client.close()
        _duckdb_client = None
