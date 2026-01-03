"""Drug and DrugVector models"""
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class Drug(Base):
    """의약품 정보 테이블"""

    __tablename__ = "drugs"

    id = Column(String(100), primary_key=True)  # 품목기준코드 (itemSeq)
    item_name = Column(String(500), nullable=False, index=True)  # 제품명
    entp_name = Column(String(200))  # 제조사
    efficacy = Column(Text)  # 효능효과 (efcyQesitm)
    use_method = Column(Text)  # 용법용량
    warning_info = Column(Text)  # 경고
    caution_info = Column(Text)  # 주의사항
    interaction = Column(Text)  # 상호작용
    side_effects = Column(Text)  # 부작용
    storage_method = Column(Text)  # 보관법
    data_source = Column(String(100), default="data.go.kr")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationship to vectors
    vectors = relationship("DrugVector", back_populates="drug", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Drug(id={self.id}, name={self.item_name})>"


class DrugVector(Base):
    """의약품 벡터 임베딩 테이블"""

    __tablename__ = "drug_vectors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    drug_id = Column(String(100), ForeignKey("drugs.id", ondelete="CASCADE"), nullable=False, index=True)
    embedding = Column(Vector(1536), nullable=False)  # OpenAI text-embedding-3-small 차원
    document = Column(Text, nullable=False)  # 원본 문서 텍스트
    chunk_index = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    # Relationship to drug
    drug = relationship("Drug", back_populates="vectors")

    def __repr__(self):
        return f"<DrugVector(id={self.id}, drug_id={self.drug_id})>"


class DocumentVector(Base):
    """문서 벡터 임베딩 테이블 (PDF, DOCX 등)"""

    __tablename__ = "document_vectors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(String(500), nullable=False, index=True)  # 파일명 또는 문서 ID
    chunk_id = Column(String(500), nullable=False, unique=True)  # 청크 고유 ID
    embedding = Column(Vector(1536), nullable=False)
    content = Column(Text, nullable=False)  # 청크 텍스트
    chunk_index = Column(Integer, default=0)
    extra_data = Column(Text)  # JSON 형태의 메타데이터
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<DocumentVector(id={self.id}, document_id={self.document_id})>"
