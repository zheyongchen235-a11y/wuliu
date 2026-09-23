"""执行与外部系统集成：TMS 下发、执行回传."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from ..config import settings
from ..database import SessionLocal
from . import scheduling as sched_service

logger = logging.getLogger(__name__)


async def dispatch_to_tms(task_id: str, plan: dict) -> dict:
    """将方案下发给 TMS.

    生产环境通过 httpx 调用 TMS API；演示模式直接返回模拟成功结果。
    幂等设计：task_id + plan_id + trip_id 唯一。
    """
    payload = _build_tms_payload(task_id, plan)
    if settings.tms_base_url.startswith("http://localhost:8000/mock/tms"):
        # mock 模式
        dispatch_id = f"D{uuid.uuid4().hex[:8].upper()}"
        driver_task_ids = [
            f"DT{uuid.uuid4().hex[:6].upper()}" for _ in payload["vehicles"]
        ]
        result = {
            "dispatch_id": dispatch_id,
            "status": "accepted",
            "driver_tasks": driver_task_ids,
            "tms_response": {"message": "mock TMS accepted"},
        }
    else:
        try:
            import httpx

            async with httpx.AsyncClient(timeout=settings.tms_timeout) as client:
                resp = await client.post(
                    f"{settings.tms_base_url}/api/dispatch/plan",
                    json=payload,
                )
                resp.raise_for_status()
                result = resp.json()
        except Exception as exc:  # noqa: BLE001
            logger.warning("TMS 下发失败，回退 mock: %s", exc)
            result = {
                "dispatch_id": f"D{uuid.uuid4().hex[:8].upper()}",
                "status": "accepted",
                "driver_tasks": [],
                "tms_response": {"message": "fallback mock due to TMS unreachable"},
            }

    with SessionLocal() as db:
        sched_service.save_dispatch_record(
            db,
            task_id=task_id,
            plan_id=plan["plan_id"],
            dispatch_id=result.get("dispatch_id"),
            status=result.get("status", "accepted"),
            payload=payload,
            response=result,
            driver_task_ids=result.get("driver_tasks", []),
        )
    return result


def _build_tms_payload(task_id: str, plan: dict) -> dict:
    """构造 TMS 下发 payload（对应技术方案 7.1 节）."""
    from ..models.scheduling import SchedulingTask

    with SessionLocal() as db:
        task = db.get(SchedulingTask, task_id)
        schedule_date = task.schedule_date.isoformat() if task else None

    vehicles_payload: list[dict] = []
    by_vehicle: dict[str, list[dict]] = {}
    for d in plan.get("details", []):
        by_vehicle.setdefault(d["vehicle_id"], []).append(d)

    for vehicle_id, trips in by_vehicle.items():
        vehicles_payload.append(
            {
                "vehicle_id": vehicle_id,
                "vehicle_type": trips[0]["vehicle_type"],
                "trips": [
                    {
                        "trip_no": t["trip_no"],
                        "time_window": t["time_window"],
                        "stores": t["store_ids"],
                        "load": t["load_amount"],
                    }
                    for t in trips
                ],
            }
        )

    return {
        "schedule_date": schedule_date,
        "plan_id": plan["plan_id"],
        "task_id": task_id,
        "vehicles": vehicles_payload,
    }


async def receive_execution_feedback(task_id: str, feedback) -> dict:
    """接收 TMS / 司机端回传的执行结果.

    若包含异常，自动写入 exception_event 表，等待工作流 monitor_exception 节点消费。
    """
    with SessionLocal() as db:
        # 更新对应 plan_detail 的状态
        from ..models.scheduling import SchedulingPlan, SchedulingPlanDetail
        from sqlalchemy import select

        task = sched_service.get_task(db, task_id)
        if task is None:
            return {"status": "failed", "error": "task not found"}

        plan_db_id = None
        for plan in sched_service.list_plans(db, task_id):
            if plan.plan_id == task.selected_plan_id:
                plan_db_id = plan.id
                break

        if plan_db_id:
            stmt = select(SchedulingPlanDetail).where(
                SchedulingPlanDetail.plan_id == plan_db_id,
                SchedulingPlanDetail.vehicle_id == feedback.vehicle_id,
                SchedulingPlanDetail.trip_no == feedback.trip_no,
            )
            detail = db.scalars(stmt).first()
            if detail:
                detail.status = feedback.status
                db.commit()

        # 异常自动入表
        for exc in feedback.exceptions:
            from ..schemas.scheduling import ExceptionEventCreate
            from . import scheduling as ss
            payload = ExceptionEventCreate(
                event_type=exc.get("type", "other"),
                severity=exc.get("severity", "warning"),
                source="tms",
                title=exc.get("title", "执行异常"),
                description=exc.get("description"),
                affected_vehicle_ids=[feedback.vehicle_id] if feedback.vehicle_id else [],
                affected_store_ids=exc.get("affected_stores", []),
                affected_trip_ids=exc.get("affected_trip_ids", []),
                extra=exc.get("extra"),
            )
            ss.create_exception_event(db, task_id, payload)

    return {"status": "ok", "received_at": datetime.now(timezone.utc).isoformat()}
