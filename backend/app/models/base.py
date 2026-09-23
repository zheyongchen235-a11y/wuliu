"""模型基类与公共混入。"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """声明式基类。"""


class GUID(String):
    """UUID 字符串类型（兼容 SQLite/PostgreSQL/MySQL）。"""

    def __init__(self, *args, length: int = 36, **kwargs):
        super().__init__(length, *args, **kwargs)

    @staticmethod
    def default() -> str:
        return str(uuid.uuid4())


class TimestampMixin:
    """created_at / updated_at 公共字段。

    使用 CURRENT_TIMESTAMP 文本以兼容 MySQL（func.now() 在 MySQL 下会编译为 now()
    函数调用，但 MySQL 不允许函数调用作为列默认值）。
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
