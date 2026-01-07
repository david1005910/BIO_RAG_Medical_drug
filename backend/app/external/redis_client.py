"""Redis 클라이언트 - 캐싱 및 메모리 저장소"""
import json
import logging
from typing import Any, Dict, List, Optional

import redis.asyncio as redis
from redis.asyncio import Redis

from app.core.config import settings
from app.external.base_memory_client import BaseMemoryClient

logger = logging.getLogger(__name__)


class RedisClient(BaseMemoryClient):
    """비동기 Redis 클라이언트 - BaseMemoryClient 구현"""

    def __init__(self, url: Optional[str] = None):
        self.url = url or settings.REDIS_URL
        self._client: Optional[Redis] = None
        self._enabled = True

    @property
    def is_enabled(self) -> bool:
        """Redis 활성화 여부"""
        return self._enabled and self._client is not None

    async def connect(self) -> bool:
        """Redis 연결"""
        try:
            self._client = redis.from_url(
                self.url,
                encoding="utf-8",
                decode_responses=True,
            )
            # 연결 테스트
            await self._client.ping()
            logger.info(f"✅ Redis 연결 성공: {self.url}")
            return True
        except Exception as e:
            logger.warning(f"⚠️ Redis 연결 실패: {e}")
            self._enabled = False
            return False

    async def close(self) -> None:
        """Redis 연결 종료"""
        if self._client:
            await self._client.close()
            logger.info("👋 Redis 연결 종료")

    # ==================== 기본 연산 ====================

    async def get(self, key: str) -> Optional[str]:
        """값 조회"""
        if not self.is_enabled:
            return None
        try:
            return await self._client.get(key)
        except Exception as e:
            logger.error(f"Redis GET 오류: {e}")
            return None

    async def set(
        self,
        key: str,
        value: str,
        ttl: Optional[int] = None,
    ) -> bool:
        """값 저장"""
        if not self.is_enabled:
            return False
        try:
            if ttl:
                await self._client.setex(key, ttl, value)
            else:
                await self._client.set(key, value)
            return True
        except Exception as e:
            logger.error(f"Redis SET 오류: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """키 삭제"""
        if not self.is_enabled:
            return False
        try:
            await self._client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis DELETE 오류: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """키 존재 여부 확인"""
        if not self.is_enabled:
            return False
        try:
            return await self._client.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis EXISTS 오류: {e}")
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

    async def set_json(
        self,
        key: str,
        value: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> bool:
        """JSON 값 저장"""
        try:
            json_str = json.dumps(value, ensure_ascii=False)
            return await self.set(key, json_str, ttl)
        except Exception as e:
            logger.error(f"Redis SET_JSON 오류: {e}")
            return False

    # ==================== 리스트 연산 ====================

    async def lpush(self, key: str, value: str) -> bool:
        """리스트 앞에 추가"""
        if not self.is_enabled:
            return False
        try:
            await self._client.lpush(key, value)
            return True
        except Exception as e:
            logger.error(f"Redis LPUSH 오류: {e}")
            return False

    async def rpush(self, key: str, value: str) -> bool:
        """리스트 뒤에 추가"""
        if not self.is_enabled:
            return False
        try:
            await self._client.rpush(key, value)
            return True
        except Exception as e:
            logger.error(f"Redis RPUSH 오류: {e}")
            return False

    async def lrange(self, key: str, start: int, end: int) -> List[str]:
        """리스트 범위 조회"""
        if not self.is_enabled:
            return []
        try:
            return await self._client.lrange(key, start, end)
        except Exception as e:
            logger.error(f"Redis LRANGE 오류: {e}")
            return []

    async def llen(self, key: str) -> int:
        """리스트 길이"""
        if not self.is_enabled:
            return 0
        try:
            return await self._client.llen(key)
        except Exception as e:
            logger.error(f"Redis LLEN 오류: {e}")
            return 0

    async def ltrim(self, key: str, start: int, end: int) -> bool:
        """리스트 트리밍 (범위 외 삭제)"""
        if not self.is_enabled:
            return False
        try:
            await self._client.ltrim(key, start, end)
            return True
        except Exception as e:
            logger.error(f"Redis LTRIM 오류: {e}")
            return False

    # ==================== TTL 연산 ====================

    async def expire(self, key: str, seconds: int) -> bool:
        """키 만료 시간 설정"""
        if not self.is_enabled:
            return False
        try:
            await self._client.expire(key, seconds)
            return True
        except Exception as e:
            logger.error(f"Redis EXPIRE 오류: {e}")
            return False

    async def ttl(self, key: str) -> int:
        """키 남은 TTL 조회"""
        if not self.is_enabled:
            return -1
        try:
            return await self._client.ttl(key)
        except Exception as e:
            logger.error(f"Redis TTL 오류: {e}")
            return -1

    # ==================== 증감 연산 ====================

    async def incr(self, key: str) -> int:
        """정수 값 증가"""
        if not self.is_enabled:
            return 0
        try:
            return await self._client.incr(key)
        except Exception as e:
            logger.error(f"Redis INCR 오류: {e}")
            return 0

    # ==================== 유틸리티 ====================

    async def keys(self, pattern: str) -> List[str]:
        """패턴 매칭 키 조회"""
        if not self.is_enabled:
            return []
        try:
            return await self._client.keys(pattern)
        except Exception as e:
            logger.error(f"Redis KEYS 오류: {e}")
            return []

    async def flush_all(self) -> bool:
        """모든 데이터 삭제 (주의: 전체 삭제)"""
        if not self.is_enabled:
            return False
        try:
            await self._client.flushall()
            logger.warning("⚠️ Redis 전체 데이터 삭제됨")
            return True
        except Exception as e:
            logger.error(f"Redis FLUSHALL 오류: {e}")
            return False


# 싱글톤 인스턴스
_redis_client: Optional[RedisClient] = None


def get_redis_client() -> RedisClient:
    """Redis 클라이언트 싱글톤 반환"""
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
    return _redis_client


async def initialize_redis() -> bool:
    """Redis 초기화"""
    client = get_redis_client()
    return await client.connect()


async def close_redis():
    """Redis 종료"""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
