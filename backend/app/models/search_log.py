"""Search log model for analytics"""
import uuid

from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class SearchLog(Base):
    """검색 로그 테이블 (익명화된 분석용)"""

    __tablename__ = "search_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query = Column(String(500), nullable=False)  # 검색 쿼리
    result_count = Column(Integer, default=0)  # 결과 수
    response_time_ms = Column(Integer)  # 응답 시간 (밀리초)
    session_hash = Column(String(64))  # 세션 해시 (익명화)
    created_at = Column(DateTime, server_default=func.now(), index=True)

    def __repr__(self):
        return f"<SearchLog(id={self.id}, query={self.query[:30]}...)>"
