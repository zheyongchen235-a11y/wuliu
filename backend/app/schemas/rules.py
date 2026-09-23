"""规则 schemas。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from .common import ORMModel


class TerrainRuleOut(ORMModel):
    id: str
    terrain_type: str
    description: str | None
    allowed_vehicle_types: list[str]


class TripRuleOut(ORMModel):
    id: str
    vehicle_type: str
    daily_trips: int
    am_trips: int
    pm_trips: int


class LoadRuleOut(ORMModel):
    id: str
    vehicle_type: str
    min_load: int
    max_load: int


class ConstraintConfigCreate(BaseModel):
    version: str
    name: str
    description: str | None = None
    hard_constraints: dict = Field(default_factory=dict)
    soft_constraints: dict = Field(default_factory=dict)
    weights: dict = Field(
        default_factory=lambda: {
            "w_4m2_usage": 0.30,
            "w_load_rate": 0.25,
            "w_trip_achievement": 0.25,
            "w_cost": 0.10,
            "w_soft_penalty": 0.10,
        }
    )
    is_active: bool = True


class ConstraintConfigOut(ORMModel):
    id: str
    version: str
    name: str
    description: str | None
    hard_constraints: dict
    soft_constraints: dict
    weights: dict
    is_active: bool
