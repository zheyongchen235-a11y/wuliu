"""规则配置模型：地形规则、趟次规则、装载规则、约束配置、规则快照。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, GUID, TimestampMixin


class TerrainRule(Base, TimestampMixin):
    """地形规则：普通/中控/严控 + 允许车辆类型。"""

    __tablename__ = "terrain_rule"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    terrain_type: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    allowed_vehicle_types: Mapped[list] = mapped_column(JSON, default=list)
    # 例：["4m2", "big", "small"] / ["big", "small"] / ["small"]


class TripRule(Base, TimestampMixin):
    """趟次规则：按车型定义每日趟次与上下午拆分。"""

    __tablename__ = "trip_rule"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    vehicle_type: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    daily_trips: Mapped[int] = mapped_column(Integer, nullable=False)
    am_trips: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    pm_trips: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class LoadRule(Base, TimestampMixin):
    """装载量规则：按车型定义最低/最高装载量。"""

    __tablename__ = "load_rule"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    vehicle_type: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    min_load: Mapped[int] = mapped_column(Integer, nullable=False)
    max_load: Mapped[int] = mapped_column(Integer, nullable=False)


class ConstraintConfig(Base, TimestampMixin):
    """约束配置中心：硬/软约束、车型优先级、保障规则、评分权重等。

    使用 JSON 字段承载具体规则体，便于版本化与热更新。
    """

    __tablename__ = "constraint_config"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=GUID.default)
    version: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    hard_constraints: Mapped[dict] = mapped_column(JSON, default=dict)
    soft_constraints: Mapped[dict] = mapped_column(JSON, default=dict)
    # 评分权重
    weights: Mapped[dict] = mapped_column(
        JSON,
        default=lambda: {
            "w_4m2_usage": 0.30,
            "w_load_rate": 0.25,
            "w_trip_achievement": 0.25,
            "w_cost": 0.10,
            "w_soft_penalty": 0.10,
        },
    )
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class ConstraintSnapshot(Base, TimestampMixin):
    """规则版本快照：每次调度任务固化当前规则版本，保证可追溯。"""

    __tablename__ = "constraint_snapshot"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=GUID.default)
    task_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("scheduling_task.id", ondelete="CASCADE"), nullable=False
    )
    rule_version: Mapped[str] = mapped_column(String(32), nullable=False)
    hard_constraints: Mapped[dict] = mapped_column(JSON, default=dict)
    soft_constraints: Mapped[dict] = mapped_column(JSON, default=dict)
    weights: Mapped[dict] = mapped_column(JSON, default=dict)
