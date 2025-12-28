"""Disease and DiseaseVector models for health information"""
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class Disease(Base):
    """질병 정보 테이블"""

    __tablename__ = "diseases"

    id = Column(String(100), primary_key=True)  # 질병 코드 (KCD code 또는 자체 ID)
    name = Column(String(500), nullable=False, index=True)  # 질병명
    name_en = Column(String(500))  # 영문 질병명
    category = Column(String(200))  # 분류 (내과, 외과 등)

    # 핵심 정보
    description = Column(Text)  # 질병 개요/설명
    causes = Column(Text)  # 원인
    symptoms = Column(Text)  # 증상
    diagnosis = Column(Text)  # 진단 방법
    treatment = Column(Text)  # 치료 방법
    prevention = Column(Text)  # 예방법

    # 추가 정보
    risk_factors = Column(Text)  # 위험 요인
    complications = Column(Text)  # 합병증
    prognosis = Column(Text)  # 예후
    related_drugs = Column(Text)  # 관련 의약품 (JSON 또는 comma-separated)

    # 메타데이터
    data_source = Column(String(200), default="manual")  # 데이터 출처
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationship to vectors
    vectors = relationship("DiseaseVector", back_populates="disease", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Disease(id={self.id}, name={self.name})>"


class DiseaseVector(Base):
    """질병 벡터 임베딩 테이블"""

    __tablename__ = "disease_vectors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    disease_id = Column(String(100), ForeignKey("diseases.id", ondelete="CASCADE"), nullable=False, index=True)
    embedding = Column(Vector(1536), nullable=False)  # OpenAI text-embedding-3-small 차원
    document = Column(Text, nullable=False)  # 원본 문서 텍스트
    chunk_index = Column(Integer, default=0)
    chunk_type = Column(String(50))  # symptoms, causes, treatment 등
    created_at = Column(DateTime, server_default=func.now())

    # Relationship to disease
    disease = relationship("Disease", back_populates="vectors")

    def __repr__(self):
        return f"<DiseaseVector(id={self.id}, disease_id={self.disease_id})>"
