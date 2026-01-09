"""Drug-related Pydantic schemas"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class DrugBase(BaseModel):
    """Base drug schema with common fields"""

    item_name: str = Field(..., description="제품명")
    entp_name: Optional[str] = Field(None, description="제조사")
    efficacy: Optional[str] = Field(None, description="효능효과")
    use_method: Optional[str] = Field(None, description="용법용량")
    warning_info: Optional[str] = Field(None, description="경고")
    caution_info: Optional[str] = Field(None, description="주의사항")
    interaction: Optional[str] = Field(None, description="상호작용")
    side_effects: Optional[str] = Field(None, description="부작용")
    storage_method: Optional[str] = Field(None, description="보관법")


class DrugCreate(DrugBase):
    """Schema for creating a new drug"""

    id: str = Field(..., description="품목기준코드")
    data_source: str = Field(default="data.go.kr", description="데이터 출처")


class DrugResponse(BaseModel):
    """Schema for drug list response"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    item_name: str
    entp_name: Optional[str]
    efficacy: Optional[str]


class DrugDetail(DrugBase):
    """Schema for detailed drug response"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    data_source: str
    created_at: datetime
    updated_at: datetime
