"""报表聚合服务。"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select

from ..models.execution import DispatchRecord
from ..models.scheduling import SchedulingPlan, SchedulingPlanDetail, SchedulingTask
from ..schemas.report import (
    AttendanceReport,
    LoadRateReport,
    TripAchievementReport,
)


def build_attendance_report(db, schedule_date: date) -> list[AttendanceReport]:
    """车辆出勤报表：按车型统计当日出勤。"""
    tasks = list(
        db.scalars(
            select(SchedulingTask).where(SchedulingTask.schedule_date == schedule_date)
        )
    )
    by_type: dict[str, dict] = {}
    for task in tasks:
        for plan in list(db.scalars(select(SchedulingPlan).where(SchedulingPlan.task_id == task.id))):
            for d in list(db.scalars(select(SchedulingPlanDetail).where(SchedulingPlanDetail.plan_id == plan.id))):
                bucket = by_type.setdefault(
                    d.vehicle_type, {"used": set(), "max": 0}
                )
                bucket["used"].add(d.vehicle_id)
    fleet = {
        "4m2": 28,
        "big": 3,
        "small": 9,
    }
    out: list[AttendanceReport] = []
    for vtype, total in fleet.items():
        used = len(by_type.get(vtype, {}).get("used", set()))
        out.append(
            AttendanceReport(
                schedule_date=schedule_date,
                vehicle_type=vtype,
                total_vehicles=total,
                used_vehicles=used,
                idle_vehicles=total - used,
                attendance_rate=round(used / total, 4) if total else 0.0,
            )
        )
    return out


def build_load_rate_report(db, schedule_date: date) -> list[LoadRateReport]:
    """装载率报表。"""
    tasks = list(
        db.scalars(
            select(SchedulingTask).where(SchedulingTask.schedule_date == schedule_date)
        )
    )
    rows: list[LoadRateReport] = []
    fleet_max = {"4m2": 800, "big": 420, "small": 300}
    for task in tasks:
        plans = list(db.scalars(select(SchedulingPlan).where(SchedulingPlan.task_id == task.id)))
        for plan in plans:
            details = list(db.scalars(select(SchedulingPlanDetail).where(SchedulingPlanDetail.plan_id == plan.id)))
            for d in details:
                max_load = fleet_max.get(d.vehicle_type, 0)
                rows.append(
                    LoadRateReport(
                        schedule_date=schedule_date,
                        vehicle_id=d.vehicle_id,
                        vehicle_type=d.vehicle_type,
                        trip_no=d.trip_no,
                        load_amount=d.load_amount,
                        max_load=max_load,
                        load_rate=round(d.load_amount / max_load, 4) if max_load else 0.0,
                    )
                )
    return rows


def build_trip_achievement_report(db, schedule_date: date) -> list[TripAchievementReport]:
    """趟次达成报表。"""
    fleet_planned = {"4m2": 2, "big": 2, "small": 4}
    fleet_count = {"4m2": 28, "big": 3, "small": 9}

    tasks = list(
        db.scalars(
            select(SchedulingTask).where(SchedulingTask.schedule_date == schedule_date)
        )
    )
    by_type: dict[str, dict] = {}
    for task in tasks:
        plans = list(db.scalars(select(SchedulingPlan).where(SchedulingPlan.task_id == task.id)))
        for plan in plans:
            details = list(db.scalars(select(SchedulingPlanDetail).where(SchedulingPlanDetail.plan_id == plan.id)))
            for d in details:
                bucket = by_type.setdefault(d.vehicle_type, {"trips": 0, "vehicles": set()})
                bucket["trips"] += 1
                bucket["vehicles"].add(d.vehicle_id)

    out: list[TripAchievementReport] = []
    for vtype, planned_per_vehicle in fleet_planned.items():
        total_vehicles = fleet_count[vtype]
        planned_total = total_vehicles * planned_per_vehicle
        completed = by_type.get(vtype, {}).get("trips", 0)
        out.append(
            TripAchievementReport(
                schedule_date=schedule_date,
                vehicle_type=vtype,
                planned_trips=planned_total,
                completed_trips=completed,
                achievement_rate=round(completed / planned_total, 4) if planned_total else 0.0,
            )
        )
    return out
