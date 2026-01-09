"""Common API response schemas"""
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Generic API response wrapper"""

    success: bool = True
    data: Optional[T] = None
    message: Optional[str] = None
    error: Optional[str] = None


class PaginationMeta(BaseModel):
    """Pagination metadata"""

    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    total_items: int = Field(..., ge=0)
    total_pages: int = Field(..., ge=0)


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper"""

    success: bool = True
    data: List[T]
    meta: PaginationMeta


class HealthResponse(BaseModel):
    """Health check response"""

    status: str = "healthy"
    version: str = "1.0.0"
    database: str = "connected"
