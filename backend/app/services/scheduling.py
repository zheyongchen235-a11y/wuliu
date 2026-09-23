"""调度任务服务：任务创建/查询、方案查询、确认、重排、报告。"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..models.basic import Driver, Route, Store, StoreRouteMapping, Vehicle, VehicleTerrainCapability
from ..models.execution import DispatchRecord, ExceptionEvent
from ..models.rules import ConstraintConfig, ConstraintSnapshot
from ..models.scheduling import (
    ReplanRecord,
    SchedulingConfirmation,
    SchedulingPlan,
    SchedulingPlanDetail,
    SchedulingPlanScore,
    SchedulingReport,
    SchedulingTask,
    SchedulingTaskSnapshot,
)
from ..schemas.scheduling import CreateTaskRequest, ConfirmRequest, ReplanRequest
from . import rules as rules_service
from .ws import ws_manager


def create_task(db: Session, req: CreateTaskRequest) -> SchedulingTask:
    # 确定规则版本
    if req.rule_version:
        cfg = rules_service.get_constraint_config_by_version(db, req.rule_version)
        if cfg is None:
            raise ValueError(f"规则版本 {req.rule_version} 不存在")
    else:
        cfg = rules_service.get_active_constraint_config(db)
    rule_version = cfg.version if cfg else None
    task = SchedulingTask(
        schedule_date=req.schedule_date,
        time_window=req.time_window,
        tenant_id=req.tenant_id,
        status="created",
        rule_version=rule_version,
        extra=req.extra,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_task(db: Session, task_id: str) -> SchedulingTask | None:
    return db.get(SchedulingTask, task_id)


def list_tasks(
    db: Session,
    *,
    schedule_date: date | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[SchedulingTask]:
    stmt = select(SchedulingTask).order_by(SchedulingTask.created_at.desc())
    if schedule_date:
        stmt = stmt.where(SchedulingTask.schedule_date == schedule_date)
    if status:
        stmt = stmt.where(SchedulingTask.status == status)
    return list(db.scalars(stmt.limit(limit).offset(offset)))


def update_task_status(
    db: Session,
    task_id: str,
    *,
    status: str | None = None,
    current_node: str | None = None,
    error_message: str | None = None,
    selected_plan_id: str | None = None,
    replan_count: int | None = None,
) -> SchedulingTask | None:
    task = db.get(SchedulingTask, task_id)
    if task is None:
        return None
    if status is not None:
        task.status = status
    if current_node is not None:
        task.current_node = current_node
    if error_message is not None:
        task.error_message = error_message
    if selected_plan_id is not None:
        task.selected_plan_id = selected_plan_id
    if replan_count is not None:
        task.replan_count = replan_count
    db.commit()
    db.refresh(task)
    return task


def snapshot_task_data(db: Session, task_id: str) -> SchedulingTaskSnapshot:
    """固化任务数据快照：门店、车辆、线路、地形、货量.

    演示模式：货量来自随机生成（生产应来自 OMS 接口 / store_demand 表）。
    """
    import random

    rng = random.Random(task_id[:8] if task_id else "42")
    stores = list(db.scalars(select(Store)))
    routes = list(db.scalars(select(Route)))
    mappings = list(db.scalars(select(StoreRouteMapping)))
    vehicles = list(db.scalars(select(Vehicle).options(selectinload(Vehicle.terrain_capability))))
    terrain_rules = list(db.scalars(select(ConstraintConfig)))

    # 为每个 enabled 门店生成 50-300 的当日货量（演示用）
    demand_by_store: dict[str, int] = {}
    for s in stores:
        if not s.enabled:
            continue
        # 30% 概率无货量
        if rng.random() < 0.2:
            demand_by_store[s.id] = 0
        else:
            demand_by_store[s.id] = rng.randint(50, 280)

    def _store_to_dict(s: Store) -> dict:
        return {
            "id": s.id,
            "name": s.name,
            "terrain_type": s.terrain_type,
            "time_window": s.time_window,
            "priority": s.priority,
            "demand": demand_by_store.get(s.id, 0),
        }

    def _vehicle_to_dict(v: Vehicle) -> dict:
        caps = {c.terrain_type: c.can_access for c in v.terrain_capability}
        return {
            "id": v.id,
            "plate": v.plate,
            "vehicle_type": v.vehicle_type,
            "min_load": v.min_load,
            "max_load": v.max_load,
            "max_trips_per_day": v.max_trips_per_day,
            "driver_id": v.driver_id,
            "status": v.status,
            "enabled": v.enabled,
            "terrain_capability": caps,
        }

    snapshot = SchedulingTaskSnapshot(
        task_id=task_id,
        stores=[_store_to_dict(s) for s in stores],
        vehicles=[_vehicle_to_dict(v) for v in vehicles],
        routes=[{"id": r.id, "name": r.name, "terrain_type": r.terrain_type} for r in routes],
        store_route_mappings=[
            {"store_id": m.store_id, "route_id": m.route_id, "is_primary": m.is_primary}
            for m in mappings
        ],
        terrain_rules=[{"version": t.version} for t in terrain_rules],
        demands=[{"store_id": sid, "demand": d} for sid, d in demand_by_store.items()],
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def get_snapshot(db: Session, task_id: str) -> SchedulingTaskSnapshot | None:
    return db.scalars(
        select(SchedulingTaskSnapshot)
        .where(SchedulingTaskSnapshot.task_id == task_id)
        .order_by(SchedulingTaskSnapshot.created_at.desc())
        .limit(1)
    ).first()


def get_rule_snapshot(db: Session, task_id: str) -> ConstraintSnapshot | None:
    return db.scalars(
        select(ConstraintSnapshot)
        .where(ConstraintSnapshot.task_id == task_id)
        .order_by(ConstraintSnapshot.created_at.desc())
        .limit(1)
    ).first()


def save_plans(db: Session, task_id: str, plans: list[dict]) -> list[SchedulingPlan]:
    """持久化工作流返回的方案列表。"""
    # 清空旧方案（若有）
    db.query(SchedulingPlan).filter(SchedulingPlan.task_id == task_id).delete()
    saved: list[SchedulingPlan] = []
    for p in plans:
        plan = SchedulingPlan(
            task_id=task_id,
            plan_id=p["plan_id"],
            name=p["name"],
            strategy=p["strategy"],
            solver_type=p.get("solver_type", "heuristic"),
            status="scored" if p.get("score") else "candidate",
            total_load=p.get("total_load", 0),
            total_trips=p.get("total_trips", 0),
            used_vehicles=p.get("used_vehicles", 0),
            avg_load_rate=p.get("avg_load_rate", 0.0),
            big_small_achievement=p.get("big_small_achievement", 0.0),
            four_two_usage=p.get("four_two_usage", 0.0),
            estimated_cost=p.get("estimated_cost", 0.0),
            summary=p.get("summary"),
        )
        db.add(plan)
        db.flush()
        for d in p.get("details", []):
            db.add(
                SchedulingPlanDetail(
                    plan_id=plan.id,
                    vehicle_id=d["vehicle_id"],
                    vehicle_type=d["vehicle_type"],
                    trip_no=d["trip_no"],
                    time_window=d["time_window"],
                    store_ids=d["store_ids"],
                    load_amount=d["load_amount"],
                    sequence=d.get("sequence", 0),
                    status="pending",
                )
            )
        score_data = p.get("score")
        if score_data:
            db.add(
                SchedulingPlanScore(
                    plan_id=plan.id,
                    total_score=score_data.get("total_score", 0.0),
                    score_4m2_usage=score_data.get("score_4m2_usage", 0.0),
                    score_load_rate=score_data.get("score_load_rate", 0.0),
                    score_trip_achievement=score_data.get("score_trip_achievement", 0.0),
                    score_cost=score_data.get("score_cost", 0.0),
                    score_soft_penalty=score_data.get("score_soft_penalty", 0.0),
                    hard_constraint_violations=score_data.get("hard_constraint_violations", []),
                    soft_constraint_violations=score_data.get("soft_constraint_violations", []),
                    explanation=score_data.get("explanation"),
                )
            )
        saved.append(plan)
    db.commit()
    for sp in saved:
        db.refresh(sp)
    return saved


def list_plans(db: Session, task_id: str) -> list[SchedulingPlan]:
    stmt = (
        select(SchedulingPlan)
        .where(SchedulingPlan.task_id == task_id)
        .options(
            selectinload(SchedulingPlan.details),
            selectinload(SchedulingPlan.score),
        )
        .order_by(SchedulingPlan.plan_id)
    )
    return list(db.scalars(stmt))


def get_plan(db: Session, plan_db_id: str) -> SchedulingPlan | None:
    return db.scalar(
        select(SchedulingPlan)
        .where(SchedulingPlan.id == plan_db_id)
        .options(
            selectinload(SchedulingPlan.details),
            selectinload(SchedulingPlan.score),
        )
    )


def confirm_plan(db: Session, task_id: str, req: ConfirmRequest) -> SchedulingConfirmation:
    task = get_task(db, task_id)
    if task is None:
        raise ValueError(f"任务 {task_id} 不存在")
    confirmation = SchedulingConfirmation(
        task_id=task_id,
        plan_id=req.plan_id,
        approved=req.approved,
        adjustments=req.adjustments,
        operator=req.operator,
        comment=req.comment,
    )
    db.add(confirmation)
    if req.approved:
        task.selected_plan_id = req.plan_id
        task.status = "confirmed"
        # 标记所选方案
        for plan in list_plans(db, task_id):
            if plan.plan_id == req.plan_id:
                plan.status = "approved"
            elif plan.status == "candidate":
                plan.status = "rejected"
    else:
        task.status = "created"
    db.commit()
    db.refresh(confirmation)
    return confirmation


def create_exception_event(
    db: Session, task_id: str, payload
) -> ExceptionEvent:
    event = ExceptionEvent(
        task_id=task_id,
        event_type=payload.event_type,
        severity=payload.severity,
        source=payload.source,
        title=payload.title,
        description=payload.description,
        affected_vehicle_ids=payload.affected_vehicle_ids,
        affected_store_ids=payload.affected_store_ids,
        affected_trip_ids=payload.affected_trip_ids,
        extra=payload.extra,
        status="open",
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def list_exceptions(db: Session, task_id: str) -> list[ExceptionEvent]:
    return list(
        db.scalars(
            select(ExceptionEvent)
            .where(ExceptionEvent.task_id == task_id)
            .order_by(ExceptionEvent.created_at.desc())
        )
    )


def create_replan_record(
    db: Session,
    task_id: str,
    *,
    trigger: str,
    reason: str | None,
    locked_trip_ids: list[str],
    before_plan_id: str | None,
    after_plan_id: str | None,
    strategy: str = "partial",
) -> ReplanRecord:
    task = get_task(db, task_id)
    new_count = (task.replan_count + 1) if task else 1
    rec = ReplanRecord(
        task_id=task_id,
        replan_count=new_count,
        trigger=trigger,
        reason=reason,
        locked_trip_ids=locked_trip_ids,
        before_plan_id=before_plan_id,
        after_plan_id=after_plan_id,
        strategy=strategy,
    )
    db.add(rec)
    if task:
        task.replan_count = new_count
        task.status = "replanning"
    db.commit()
    db.refresh(rec)
    return rec


def save_dispatch_record(
    db: Session,
    task_id: str,
    plan_id: str,
    *,
    dispatch_id: str | None,
    status: str,
    payload: dict | None,
    response: dict | None,
    driver_task_ids: list | None,
    error_message: str | None = None,
) -> DispatchRecord:
    rec = DispatchRecord(
        task_id=task_id,
        plan_id=plan_id,
        dispatch_id=dispatch_id,
        status=status,
        payload=payload,
        response=response,
        driver_task_ids=driver_task_ids or [],
        dispatched_at=datetime.now(timezone.utc) if status == "accepted" else None,
        error_message=error_message,
    )
    db.add(rec)
    task = get_task(db, task_id)
    if task:
        task.status = "dispatched" if status == "accepted" else task.status
    db.commit()
    db.refresh(rec)
    return rec


def save_report(
    db: Session,
    task_id: str,
    *,
    report_type: str,
    content: str,
    metrics: dict | None,
) -> SchedulingReport:
    report = SchedulingReport(
        task_id=task_id,
        report_type=report_type,
        content=content,
        metrics=metrics,
    )
    db.add(report)
    task = get_task(db, task_id)
    if task and task.status not in ("completed", "failed"):
        task.status = "completed"
    db.commit()
    db.refresh(report)
    return report


def get_report(db: Session, task_id: str) -> SchedulingReport | None:
    return db.scalars(
        select(SchedulingReport)
        .where(SchedulingReport.task_id == task_id)
        .order_by(SchedulingReport.created_at.desc())
        .limit(1)
    ).first()


async def publish_progress(
    task_id: str,
    *,
    node: str,
    status: str,
    message: str,
    progress: int,
    extra: dict | None = None,
) -> None:
    await ws_manager.broadcast(
        task_id,
        {
            "task_id": task_id,
            "node": node,
            "status": status,
            "message": message,
            "progress": progress,
            "extra": extra or {},
        },
    )
