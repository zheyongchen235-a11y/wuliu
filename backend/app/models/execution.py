"""执行与异常：下发记录、异常事件。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, GUID, TimestampMixin


class DispatchRecord(Base, TimestampMixin):
    """调度方案下发到 TMS 的执行记录。"""

    __tablename__ = "dispatch_record"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=GUID.default)
    task_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("scheduling_task.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plan_id: Mapped[str] = mapped_column(String(32), nullable=False)
    dispatch_id: Mapped[str | None] = mapped_column(String(64))
    # TMS 返回的下发单号
    target_system: Mapped[str] = mapped_column(String(32), default="TMS")
    status: Mapped[str] = mapped_column(String(32), default="pending")
    # pending / accepted / rejected / completed / failed
    payload: Mapped[dict | None] = mapped_column(JSON)
    response: Mapped[dict | None] = mapped_column(JSON)
    driver_task_ids: Mapped[list] = mapped_column(JSON, default=list)
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)


class ExceptionEvent(Base, TimestampMixin):
    """异常事件：车辆故障、司机缺勤、货量变更、交通管制等。"""

    __tablename__ = "exception_event"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=GUID.default)
    task_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("scheduling_task.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    # vehicle_failure / driver_absence / demand_change / traffic / terrain_lock / other
    severity: Mapped[str] = mapped_column(String(16), default="warning")
    # info / warning / critical
    source: Mapped[str] = mapped_column(String(32), default="manual")
    # manual / tms / driver / system
    title: Mapped[str] = mapped_column(String(256))
    description: Mapped[str | None] = mapped_column(Text)
    affected_vehicle_ids: Mapped[list] = mapped_column(JSON, default=list)
    affected_store_ids: Mapped[list] = mapped_column(JSON, default=list)
    affected_trip_ids: Mapped[list] = mapped_column(JSON, default=list)
    extra: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(16), default="open")
    # open / handling / resolved / ignored
    handled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
