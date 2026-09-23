"""报表 schemas。"""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class AttendanceReport(BaseModel):
    """车辆出勤报表。"""

    schedule_date: date
    vehicle_type: str
    total_vehicles: int
    used_vehicles: int
    idle_vehicles: int
    attendance_rate: float


class LoadRateReport(BaseModel):
    """装载率报表。"""

    schedule_date: date
    vehicle_id: str
    vehicle_type: str
    trip_no: int
    load_amount: int
    max_load: int
    load_rate: float


class TripAchievementReport(BaseModel):
    """趟次达成报表。"""

    schedule_date: date
    vehicle_type: str
    planned_trips: int
    completed_trips: int
    achievement_rate: float


class ReportOut(BaseModel):
    task_id: str
    report_type: str
    content: str
    metrics: dict | None = None
