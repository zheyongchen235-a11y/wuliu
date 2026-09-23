"""调度 schemas。"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from .common import ORMModel


class CreateTaskRequest(BaseModel):
    """创建调度任务。"""

    schedule_date: date
    time_window: str = "all"  # all / AM / PM
    tenant_id: str = "default"
    rule_version: str | None = None  # 不指定则取当前激活版本
    extra: dict | None = None


class PlanDetailOut(ORMModel):
    id: str
    vehicle_id: str
    vehicle_type: str
    trip_no: int
    time_window: str
    store_ids: list[str]
    load_amount: int
    sequence: int
    status: str


class PlanScoreOut(ORMModel):
    total_score: float
    score_4m2_usage: float
    score_load_rate: float
    score_trip_achievement: float
    score_cost: float
    score_soft_penalty: float
    hard_constraint_violations: list
    soft_constraint_violations: list
    explanation: str | None


class PlanOut(ORMModel):
    id: str
    task_id: str
    plan_id: str
    name: str
    strategy: str
    solver_type: str
    status: str
    total_load: int
    total_trips: int
    used_vehicles: int
    avg_load_rate: float
    big_small_achievement: float
    four_two_usage: float
    estimated_cost: float
    summary: dict | None
    details: list[PlanDetailOut] = Field(default_factory=list)
    score: PlanScoreOut | None = None


class TaskOut(ORMModel):
    id: str
    tenant_id: str
    schedule_date: date
    time_window: str
    status: str
    rule_version: str | None
    selected_plan_id: str | None
    replan_count: int
    current_node: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class ConfirmRequest(BaseModel):
    """人工确认请求。"""

    approved: bool
    plan_id: str
    adjustments: list[dict] = Field(default_factory=list)
    operator: str | None = None
    comment: str | None = None


class ReplanRequest(BaseModel):
    """人工触发重排。"""

    trigger: str = "manual"
    reason: str | None = None
    locked_trip_ids: list[str] = Field(default_factory=list)


class ExceptionEventCreate(BaseModel):
    event_type: str
    severity: str = "warning"
    source: str = "manual"
    title: str
    description: str | None = None
    affected_vehicle_ids: list[str] = Field(default_factory=list)
    affected_store_ids: list[str] = Field(default_factory=list)
    affected_trip_ids: list[str] = Field(default_factory=list)
    extra: dict | None = None


class ExceptionEventOut(ORMModel):
    id: str
    task_id: str
    event_type: str
    severity: str
    source: str
    title: str
    description: str | None
    affected_vehicle_ids: list
    affected_store_ids: list
    status: str
    created_at: datetime


class ExecutionFeedback(BaseModel):
    """TMS / 司机端回传的执行结果。"""

    dispatch_id: str | None = None
    vehicle_id: str
    trip_no: int = 1
    status: str  # completed / partial / failed
    actual_load: int | None = None
    stores_completed: list[str] = Field(default_factory=list)
    exceptions: list[dict] = Field(default_factory=list)


class TaskProgressMessage(BaseModel):
    """WebSocket 推送的进度消息。"""

    task_id: str
    node: str
    status: str  # running / done / error / awaiting_confirmation
    message: str
    progress: int = 0  # 0-100
    timestamp: datetime
    extra: dict | None = None
