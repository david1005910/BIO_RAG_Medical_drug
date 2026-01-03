"""메모리 서비스 - 대화 히스토리 및 쿼리 캐싱"""
import hashlib
import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.external.redis_client import RedisClient, get_redis_client
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ConversationTurn:
    """대화 턴 데이터"""
    query: str
    response: str
    sources: List[Dict[str, Any]]
    timestamp: str
    query_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationTurn":
        return cls(**data)


@dataclass
class CachedResponse:
    """캐시된 응답 데이터"""
    query: str
    response: str
    sources: List[Dict[str, Any]]
    cached_at: str
    hit_count: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CachedResponse":
        return cls(**data)


class MemoryService:
    """대화 메모리 및 캐싱 서비스

    기능:
    1. 쿼리 캐싱 - 동일 쿼리에 대한 응답 캐싱
    2. 대화 히스토리 - 세션별 대화 기록 저장
    3. 중복 검색 판별 - 쿼리 해시로 중복 확인
    4. 컨텍스트 참조 - 이전 대화 참조하여 응답 생성
    """

    # Redis 키 프리픽스
    CACHE_PREFIX = "cache:query:"
    HISTORY_PREFIX = "history:"
    SESSION_PREFIX = "session:"

    # 기본 설정
    DEFAULT_CACHE_TTL = 3600  # 1시간
    DEFAULT_HISTORY_TTL = 86400  # 24시간
    MAX_HISTORY_LENGTH = 20  # 세션당 최대 대화 수

    def __init__(
        self,
        client: Optional[RedisClient] = None,
        cache_ttl: int = DEFAULT_CACHE_TTL,
        history_ttl: int = DEFAULT_HISTORY_TTL,
        max_history: int = MAX_HISTORY_LENGTH,
    ):
        self.client = client or get_redis_client()
        self.cache_ttl = cache_ttl
        self.history_ttl = history_ttl
        self.max_history = max_history

    def is_enabled(self) -> bool:
        """메모리 서비스 활성화 여부"""
        return self.client.is_enabled()

    # ==================== 쿼리 해싱 ====================

    @staticmethod
    def hash_query(query: str) -> str:
        """쿼리를 해시값으로 변환"""
        # 정규화: 소문자, 공백 제거
        normalized = query.lower().strip()
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    # ==================== 쿼리 캐싱 ====================

    async def get_cached_response(self, query: str) -> Optional[CachedResponse]:
        """캐시된 응답 조회

        Args:
            query: 검색 쿼리

        Returns:
            캐시된 응답 또는 None
        """
        if not self.is_enabled():
            return None

        query_hash = self.hash_query(query)
        cache_key = f"{self.CACHE_PREFIX}{query_hash}"

        cached = await self.client.get_json(cache_key)
        if cached:
            # 히트 카운트 증가
            cached["hit_count"] = cached.get("hit_count", 1) + 1
            await self.client.set_json(cache_key, cached, self.cache_ttl)

            logger.info(f"🎯 캐시 히트: {query[:30]}... (hits: {cached['hit_count']})")
            return CachedResponse.from_dict(cached)

        return None

    async def cache_response(
        self,
        query: str,
        response: str,
        sources: List[Dict[str, Any]],
    ) -> bool:
        """응답 캐싱

        Args:
            query: 검색 쿼리
            response: AI 응답
            sources: 참조 소스 목록

        Returns:
            성공 여부
        """
        if not self.is_enabled():
            return False

        query_hash = self.hash_query(query)
        cache_key = f"{self.CACHE_PREFIX}{query_hash}"

        cached = CachedResponse(
            query=query,
            response=response,
            sources=sources,
            cached_at=datetime.now().isoformat(),
            hit_count=1,
        )

        success = await self.client.set_json(cache_key, cached.to_dict(), self.cache_ttl)
        if success:
            logger.info(f"💾 응답 캐싱: {query[:30]}...")
        return success

    async def is_duplicate_query(self, query: str) -> bool:
        """중복 쿼리 여부 확인

        Args:
            query: 검색 쿼리

        Returns:
            중복 여부
        """
        if not self.is_enabled():
            return False

        query_hash = self.hash_query(query)
        cache_key = f"{self.CACHE_PREFIX}{query_hash}"
        return await self.client.exists(cache_key)

    # ==================== 대화 히스토리 ====================

    async def add_to_history(
        self,
        session_id: str,
        query: str,
        response: str,
        sources: List[Dict[str, Any]],
    ) -> bool:
        """대화 히스토리에 추가

        Args:
            session_id: 세션 ID
            query: 사용자 쿼리
            response: AI 응답
            sources: 참조 소스 목록

        Returns:
            성공 여부
        """
        if not self.is_enabled():
            return False

        history_key = f"{self.HISTORY_PREFIX}{session_id}"

        turn = ConversationTurn(
            query=query,
            response=response,
            sources=sources,
            timestamp=datetime.now().isoformat(),
            query_hash=self.hash_query(query),
        )

        # 리스트에 추가
        success = await self.client.rpush(history_key, json.dumps(turn.to_dict(), ensure_ascii=False))
        if not success:
            return False

        # 히스토리 길이 제한
        length = await self.client.llen(history_key)
        if length > self.max_history:
            await self.client.ltrim(history_key, -self.max_history, -1)

        # TTL 갱신
        await self.client.expire(history_key, self.history_ttl)

        logger.info(f"📝 히스토리 추가: session={session_id}, turns={min(length, self.max_history)}")
        return True

    async def get_history(
        self,
        session_id: str,
        limit: Optional[int] = None,
    ) -> List[ConversationTurn]:
        """대화 히스토리 조회

        Args:
            session_id: 세션 ID
            limit: 최대 조회 수 (None이면 전체)

        Returns:
            대화 턴 목록 (오래된 순)
        """
        if not self.is_enabled():
            return []

        history_key = f"{self.HISTORY_PREFIX}{session_id}"

        if limit:
            # 최근 N개
            items = await self.client.lrange(history_key, -limit, -1)
        else:
            # 전체
            items = await self.client.lrange(history_key, 0, -1)

        turns = []
        for item in items:
            try:
                data = json.loads(item)
                turns.append(ConversationTurn.from_dict(data))
            except (json.JSONDecodeError, TypeError):
                continue

        return turns

    async def get_recent_context(
        self,
        session_id: str,
        limit: int = 3,
    ) -> str:
        """최근 대화 컨텍스트 문자열 생성

        Args:
            session_id: 세션 ID
            limit: 참조할 최근 대화 수

        Returns:
            포맷팅된 대화 컨텍스트
        """
        turns = await self.get_history(session_id, limit)
        if not turns:
            return ""

        context_parts = ["[이전 대화 내용]"]
        for i, turn in enumerate(turns, 1):
            context_parts.append(f"\n사용자 질문 {i}: {turn.query}")
            # 응답은 요약해서 포함 (너무 길면 잘라냄)
            response_summary = turn.response[:200] + "..." if len(turn.response) > 200 else turn.response
            context_parts.append(f"AI 답변 {i}: {response_summary}")

        return "\n".join(context_parts)

    async def clear_history(self, session_id: str) -> bool:
        """대화 히스토리 삭제

        Args:
            session_id: 세션 ID

        Returns:
            성공 여부
        """
        if not self.is_enabled():
            return False

        history_key = f"{self.HISTORY_PREFIX}{session_id}"
        return await self.client.delete(history_key)

    # ==================== 세션 관리 ====================

    async def create_session(self, session_id: str, metadata: Optional[Dict] = None) -> bool:
        """세션 생성

        Args:
            session_id: 세션 ID
            metadata: 세션 메타데이터

        Returns:
            성공 여부
        """
        if not self.is_enabled():
            return False

        session_key = f"{self.SESSION_PREFIX}{session_id}"
        session_data = {
            "created_at": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat(),
            **(metadata or {}),
        }

        return await self.client.set_json(session_key, session_data, self.history_ttl)

    async def update_session_activity(self, session_id: str) -> bool:
        """세션 활동 시간 갱신

        Args:
            session_id: 세션 ID

        Returns:
            성공 여부
        """
        if not self.is_enabled():
            return False

        session_key = f"{self.SESSION_PREFIX}{session_id}"
        session_data = await self.client.get_json(session_key)

        if session_data:
            session_data["last_active"] = datetime.now().isoformat()
            return await self.client.set_json(session_key, session_data, self.history_ttl)

        return False

    async def get_session(self, session_id: str) -> Optional[Dict]:
        """세션 정보 조회

        Args:
            session_id: 세션 ID

        Returns:
            세션 데이터 또는 None
        """
        if not self.is_enabled():
            return None

        session_key = f"{self.SESSION_PREFIX}{session_id}"
        return await self.client.get_json(session_key)

    # ==================== 통계 ====================

    async def get_stats(self) -> Dict[str, Any]:
        """메모리 서비스 통계"""
        return {
            "enabled": self.is_enabled(),
            "cache_ttl": self.cache_ttl,
            "history_ttl": self.history_ttl,
            "max_history": self.max_history,
        }


# 싱글톤 인스턴스
_memory_service: Optional[MemoryService] = None


def get_memory_service() -> MemoryService:
    """메모리 서비스 싱글톤 반환"""
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService()
    return _memory_service
