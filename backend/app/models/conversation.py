"""대화 히스토리 영구 저장 모델

PostgreSQL에 대화 히스토리를 영구 저장하기 위한 모델.
Redis/DuckDB의 임시 캐시와 함께 사용하여 영구 저장 기능 제공.
"""
from datetime import datetime
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import (
    Column, String, Text, DateTime, Integer, Float,
    JSON, Index, ForeignKey, Boolean
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class Session(Base):
    """세션 정보 테이블

    사용자의 대화 세션을 추적합니다.
    """
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(255), nullable=True, index=True)  # 익명 사용자 허용
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_activity = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    metadata_ = Column("metadata", JSON, nullable=True)  # 추가 메타데이터

    # 관계
    conversations = relationship("ConversationHistory", back_populates="session", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_sessions_user_id", "user_id"),
        Index("idx_sessions_created_at", "created_at"),
        Index("idx_sessions_last_activity", "last_activity"),
    )


class ConversationHistory(Base):
    """대화 히스토리 영구 저장 테이블

    사용자의 질문과 AI 응답을 영구 저장합니다.
    """
    __tablename__ = "conversation_history"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    turn_number = Column(Integer, nullable=False)  # 대화 턴 번호

    # 질문 정보
    query = Column(Text, nullable=False)
    query_hash = Column(String(64), nullable=False, index=True)  # SHA256 해시 (중복 감지용)

    # 응답 정보
    response = Column(Text, nullable=False)
    response_time_ms = Column(Integer, nullable=True)  # 응답 시간 (밀리초)

    # 검색 결과 메타데이터
    sources = Column(JSON, nullable=True)  # 참조한 소스 목록
    disease_results = Column(JSON, nullable=True)  # 질병 검색 결과

    # 점수 정보
    top_similarity = Column(Float, nullable=True)  # 최상위 유사도
    avg_similarity = Column(Float, nullable=True)  # 평균 유사도

    # 캐시 정보
    from_cache = Column(Boolean, default=False)

    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 관계
    session = relationship("Session", back_populates="conversations")

    __table_args__ = (
        Index("idx_conv_session_turn", "session_id", "turn_number"),
        Index("idx_conv_query_hash", "query_hash"),
        Index("idx_conv_created_at", "created_at"),
    )


class CachedQuery(Base):
    """캐시된 쿼리 영구 저장 테이블

    자주 사용되는 쿼리의 응답을 영구 캐싱합니다.
    """
    __tablename__ = "cached_queries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    query_hash = Column(String(64), unique=True, nullable=False, index=True)
    query = Column(Text, nullable=False)  # 원본 쿼리 (디버깅용)

    # 캐시된 응답
    response = Column(Text, nullable=False)
    sources = Column(JSON, nullable=True)
    disease_results = Column(JSON, nullable=True)

    # 통계
    hit_count = Column(Integer, default=0)
    last_hit_at = Column(DateTime, nullable=True)

    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # TTL (초 단위, NULL이면 영구)
    ttl_seconds = Column(Integer, nullable=True)
    expires_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_cached_query_hash", "query_hash"),
        Index("idx_cached_hit_count", "hit_count"),
        Index("idx_cached_expires_at", "expires_at"),
    )
