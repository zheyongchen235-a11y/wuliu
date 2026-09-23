"""调度任务、方案、评分、确认、报告、重排记录。"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, GUID, TimestampMixin


class SchedulingTask(Base, TimestampMixin):
    """调度任务主表。"""

    __tablename__ = "scheduling_task"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=GUID.default)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    schedule_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    time_window: Mapped[str] = mapped_column(String(16), default="all")
    # all / AM / PM
    status: Mapped[str] = mapped_column(String(32), default="created", index=True)
    # created / running / awaiting_confirmation / confirmed / dispatched / completed / failed / replanning
    rule_version: Mapped[str | None] = mapped_column(String(32))
    selected_plan_id: Mapped[str | None] = mapped_column(String(64))
    replan_count: Mapped[int] = mapped_column(Integer, default=0)
    current_node: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)
    extra: Mapped[dict | None] = mapped_column(JSON)

    plans: Mapped[list["SchedulingPlan"]] = relationship(
        "SchedulingPlan", back_populates="task", cascade="all, delete-orphan"
    )
    snapshots: Mapped[list["SchedulingTaskSnapshot"]] = relationship(
        "SchedulingTaskSnapshot", back_populates="task", cascade="all, delete-orphan"
    )
    confirmations: Mapped[list["SchedulingConfirmation"]] = relationship(
        "SchedulingConfirmation", back_populates="task", cascade="all, delete-orphan"
    )
    reports: Mapped[list["SchedulingReport"]] = relationship(
        "SchedulingReport", back_populates="task", cascade="all, delete-orphan"
    )


class SchedulingTaskSnapshot(Base, TimestampMixin):
    """任务数据快照：调度开始时刻的门店/车辆/线路/地形/货量等数据。"""

    __tablename__ = "scheduling_task_snapshot"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=GUID.default)
    task_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("scheduling_task.id", ondelete="CASCADE"), nullable=False
    )
    stores: Mapped[list] = mapped_column(JSON, default=list)
    vehicles: Mapped[list] = mapped_column(JSON, default=list)
    routes: Mapped[list] = mapped_column(JSON, default=list)
    store_route_mappings: Mapped[list] = mapped_column(JSON, default=list)
    terrain_rules: Mapped[list] = mapped_column(JSON, default=list)
    demands: Mapped[list] = mapped_column(JSON, default=list)

    task: Mapped[SchedulingTask] = relationship("SchedulingTask", back_populates="snapshots")


class SchedulingPlan(Base, TimestampMixin):
    """调度方案主表：每次求解产生一个方案。"""

    __tablename__ = "scheduling_plan"
    __table_args__ = (UniqueConstraint("task_id", "plan_id", name="uq_plan_task_plan"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=GUID.default)
    task_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("scheduling_task.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plan_id: Mapped[str] = mapped_column(String(32), nullable=False)
    # A / B / C / D
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    strategy: Mapped[str] = mapped_column(String(64), nullable=False)
    # 4m2_priority / cost_min / big_small_priority / load_balance / cpsat_optimal
    solver_type: Mapped[str] = mapped_column(String(32), default="heuristic")
    # heuristic / cpsat
    status: Mapped[str] = mapped_column(String(32), default="candidate")
    # candidate / scored / selected / approved / rejected / dispatched
    total_load: Mapped[int] = mapped_column(Integer, default=0)
    total_trips: Mapped[int] = mapped_column(Integer, default=0)
    used_vehicles: Mapped[int] = mapped_column(Integer, default=0)
    avg_load_rate: Mapped[float] = mapped_column(Float, default=0.0)
    big_small_achievement: Mapped[float] = mapped_column(Float, default=0.0)
    four_two_usage: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0)
    summary: Mapped[dict | None] = mapped_column(JSON)

    task: Mapped[SchedulingTask] = relationship("SchedulingTask", back_populates="plans")
    details: Mapped[list["SchedulingPlanDetail"]] = relationship(
        "SchedulingPlanDetail", back_populates="plan", cascade="all, delete-orphan"
    )
    score: Mapped["SchedulingPlanScore | None"] = relationship(
        "SchedulingPlanScore", back_populates="plan", uselist=False, cascade="all, delete-orphan"
    )


class SchedulingPlanDetail(Base, TimestampMixin):
    """方案明细：车辆 - 趟次 - 门店 序列。"""

    __tablename__ = "scheduling_plan_detail"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=GUID.default)
    plan_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("scheduling_plan.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vehicle_id: Mapped[str] = mapped_column(String(64), nullable=False)
    vehicle_type: Mapped[str] = mapped_column(String(32), nullable=False)
    trip_no: Mapped[int] = mapped_column(Integer, nullable=False)
    time_window: Mapped[str] = mapped_column(String(16), nullable=False)
    # AM / PM
    store_ids: Mapped[list] = mapped_column(JSON, default=list)
    load_amount: Mapped[int] = mapped_column(Integer, default=0)
    sequence: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    # pending / dispatched / in_progress / completed / canceled

    plan: Mapped[SchedulingPlan] = relationship("SchedulingPlan", back_populates="details")


class SchedulingPlanScore(Base, TimestampMixin):
    """方案评分。"""

    __tablename__ = "scheduling_plan_score"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=GUID.default)
    plan_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("scheduling_plan.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    total_score: Mapped[float] = mapped_column(Float, default=0.0)
    # 子分项
    score_4m2_usage: Mapped[float] = mapped_column(Float, default=0.0)
    score_load_rate: Mapped[float] = mapped_column(Float, default=0.0)
    score_trip_achievement: Mapped[float] = mapped_column(Float, default=0.0)
    score_cost: Mapped[float] = mapped_column(Float, default=0.0)
    score_soft_penalty: Mapped[float] = mapped_column(Float, default=0.0)
    hard_constraint_violations: Mapped[list] = mapped_column(JSON, default=list)
    soft_constraint_violations: Mapped[list] = mapped_column(JSON, default=list)
    explanation: Mapped[str | None] = mapped_column(Text)

    plan: Mapped[SchedulingPlan] = relationship("SchedulingPlan", back_populates="score")


class SchedulingConfirmation(Base, TimestampMixin):
    """人工确认记录。"""

    __tablename__ = "scheduling_confirmation"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=GUID.default)
    task_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("scheduling_task.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plan_id: Mapped[str] = mapped_column(String(32), nullable=False)
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    adjustments: Mapped[list] = mapped_column(JSON, default=list)
    operator: Mapped[str | None] = mapped_column(String(64))
    comment: Mapped[str | None] = mapped_column(Text)

    task: Mapped[SchedulingTask] = relationship("SchedulingTask", back_populates="confirmations")


class SchedulingReport(Base, TimestampMixin):
    """调度报告（自然语言 + 结构化指标）。"""

    __tablename__ = "scheduling_report"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=GUID.default)
    task_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("scheduling_task.id", ondelete="CASCADE"), nullable=False, index=True
    )
    report_type: Mapped[str] = mapped_column(String(32), default="task_summary")
    content: Mapped[str] = mapped_column(Text)
    metrics: Mapped[dict | None] = mapped_column(JSON)

    task: Mapped[SchedulingTask] = relationship("SchedulingTask", back_populates="reports")


class ReplanRecord(Base, TimestampMixin):
    """重排记录：异常触发后的重排历史。"""

    __tablename__ = "replan_record"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=GUID.default)
    task_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("scheduling_task.id", ondelete="CASCADE"), nullable=False, index=True
    )
    replan_count: Mapped[int] = mapped_column(Integer, nullable=False)
    trigger: Mapped[str] = mapped_column(String(64))
    # vehicle_failure / driver_absence / demand_change / traffic / terrain_lock / manual
    reason: Mapped[str | None] = mapped_column(Text)
    locked_trip_ids: Mapped[list] = mapped_column(JSON, default=list)
    before_plan_id: Mapped[str | None] = mapped_column(String(32))
    after_plan_id: Mapped[str | None] = mapped_column(String(32))
    strategy: Mapped[str] = mapped_column(String(32), default="partial")
    # partial / global
