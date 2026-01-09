"""추상 메모리 클라이언트 인터페이스

Redis와 DuckDB 메모리 백엔드를 위한 공통 인터페이스 정의
"""
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class BaseMemoryClient(ABC):
    """메모리 백엔드 추상 클래스

    Redis와 DuckDB 클라이언트가 구현해야 할 공통 인터페이스
    """

    @property
    @abstractmethod
    def is_enabled(self) -> bool:
        """메모리 클라이언트 활성화 여부"""
        pass

    @abstractmethod
    async def connect(self) -> bool:
        """연결 초기화"""
        pass

    @abstractmethod
    async def close(self) -> None:
        """연결 종료"""
        pass

    # ==================== 기본 연산 ====================

    @abstractmethod
    async def get(self, key: str) -> Optional[str]:
        """키에 해당하는 값 조회"""
        pass

    @abstractmethod
    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """키-값 저장 (TTL 옵션)"""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """키 삭제"""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """키 존재 여부 확인"""
        pass

    # ==================== JSON 연산 ====================

    @abstractmethod
    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """JSON 데이터 조회"""
        pass

    @abstractmethod
    async def set_json(self, key: str, data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """JSON 데이터 저장"""
        pass

    # ==================== 리스트 연산 ====================

    @abstractmethod
    async def rpush(self, key: str, value: str) -> bool:
        """리스트 끝에 값 추가"""
        pass

    @abstractmethod
    async def lpush(self, key: str, value: str) -> bool:
        """리스트 앞에 값 추가"""
        pass

    @abstractmethod
    async def lrange(self, key: str, start: int, end: int) -> List[str]:
        """리스트 범위 조회 (start ~ end)"""
        pass

    @abstractmethod
    async def llen(self, key: str) -> int:
        """리스트 길이"""
        pass

    @abstractmethod
    async def ltrim(self, key: str, start: int, end: int) -> bool:
        """리스트 트리밍 (범위 외 삭제)"""
        pass

    # ==================== TTL 연산 ====================

    @abstractmethod
    async def expire(self, key: str, seconds: int) -> bool:
        """키 만료 시간 설정"""
        pass

    @abstractmethod
    async def ttl(self, key: str) -> int:
        """키의 남은 TTL 조회 (-1: 만료 없음, -2: 키 없음)"""
        pass

    # ==================== 증감 연산 ====================

    @abstractmethod
    async def incr(self, key: str) -> int:
        """정수 값 증가"""
        pass

    # ==================== 유틸리티 ====================

    @abstractmethod
    async def keys(self, pattern: str) -> List[str]:
        """패턴 매칭 키 조회"""
        pass

    @abstractmethod
    async def flush_all(self) -> bool:
        """모든 데이터 삭제 (주의: 전체 삭제)"""
        pass
