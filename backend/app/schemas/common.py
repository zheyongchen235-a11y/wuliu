"""通用 schema 工具。"""
from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict


T = TypeVar("T")


class ORMModel(BaseModel):
    """统一 ORM 模式配置。"""

    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    """分页响应。"""

    items: list[T]
    total: int
    page: int = 1
    page_size: int = 20


class ApiResponse(BaseModel, Generic[T]):
    """统一 API 响应包络。"""

    code: int = 0
    message: str = "ok"
    data: T | None = None
