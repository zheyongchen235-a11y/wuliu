"""调度任务 API: /api/v1/scheduling/tasks/..."""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db, SessionLocal
from ..schemas.common import ApiResponse
from ..schemas.scheduling import (
    ConfirmRequest,
    CreateTaskRequest,
    ExceptionEventCreate,
    ExceptionEventOut,
    ExecutionFeedback,
    PlanOut,
    ReplanRequest,
    TaskOut,
)
from ..services import scheduling as sched_service
from ..services import execution as exec_service
from ..workflow.graph import resume_scheduling, run_scheduling

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/scheduling", tags=["调度任务"])


@router.post("/tasks", response_model=ApiResponse[TaskOut])
def create_task(req: CreateTaskRequest, db: Session = Depends(get_db)):
    try:
        task = sched_service.create_task(db, req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ApiResponse(data=TaskOut.model_validate(task))


@router.get("/tasks", response_model=ApiResponse[list[TaskOut]])
def list_tasks(
    schedule_date: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    from datetime import date as date_cls

    sd = None
    if schedule_date:
        try:
            sd = date_cls.fromisoformat(schedule_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="schedule_date 格式应为 YYYY-MM-DD")
    items = sched_service.list_tasks(db, schedule_date=sd, status=status, limit=limit, offset=offset)
    return ApiResponse(data=[TaskOut.model_validate(t) for t in items])


@router.get("/tasks/{task_id}", response_model=ApiResponse[TaskOut])
def get_task(task_id: str, db: Session = Depends(get_db)):
    task = sched_service.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return ApiResponse(data=TaskOut.model_validate(task))


@router.post("/tasks/{task_id}/start", response_model=ApiResponse[dict])
async def start_task(task_id: str, background_tasks: BackgroundTasks):
    # 后台运行工作流
    background_tasks.add_task(_safe_run, task_id)
    return ApiResponse(data={"task_id": task_id, "status": "started"})


async def _safe_run(task_id: str) -> None:
    try:
        await run_scheduling(task_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("调度任务 %s 运行失败: %s", task_id, exc)
        with SessionLocal() as db:
            sched_service.update_task_status(db, task_id, status="failed", error_message=str(exc))


@router.get("/tasks/{task_id}/plans", response_model=ApiResponse[list[PlanOut]])
def list_plans(task_id: str, db: Session = Depends(get_db)):
    plans = sched_service.list_plans(db, task_id)
    return ApiResponse(data=[PlanOut.model_validate(p) for p in plans])


@router.get("/tasks/{task_id}/plans/{plan_id}", response_model=ApiResponse[PlanOut])
def get_plan(task_id: str, plan_id: str, db: Session = Depends(get_db)):
    plans = sched_service.list_plans(db, task_id)
    for p in plans:
        if p.plan_id == plan_id:
            return ApiResponse(data=PlanOut.model_validate(p))
    raise HTTPException(status_code=404, detail="Plan not found")


@router.post("/tasks/{task_id}/confirm", response_model=ApiResponse[dict])
async def confirm_task(task_id: str, req: ConfirmRequest, background_tasks: BackgroundTasks):
    with SessionLocal() as db:
        sched_service.confirm_plan(db, task_id, req)
    # 恢复工作流
    background_tasks.add_task(_safe_resume, task_id, req.model_dump())
    return ApiResponse(data={"task_id": task_id, "status": "resumed"})


async def _safe_resume(task_id: str, payload: dict) -> None:
    try:
        await resume_scheduling(task_id, payload)
    except Exception as exc:  # noqa: BLE001
        logger.exception("调度任务 %s 恢复失败: %s", task_id, exc)
        with SessionLocal() as db:
            sched_service.update_task_status(db, task_id, status="failed", error_message=str(exc))


@router.post("/tasks/{task_id}/replan", response_model=ApiResponse[dict])
async def replan_task(task_id: str, req: ReplanRequest, background_tasks: BackgroundTasks):
    with SessionLocal() as db:
        task = sched_service.get_task(db, task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        before_plan_id = task.selected_plan_id
        sched_service.create_replan_record(
            db, task_id,
            trigger=req.trigger,
            reason=req.reason,
            locked_trip_ids=req.locked_trip_ids,
            before_plan_id=before_plan_id,
            after_plan_id=None,
            strategy="partial",
        )
        # 注入异常事件作为重排入口
        from ..schemas.scheduling import ExceptionEventCreate
        sched_service.create_exception_event(
            db, task_id,
            ExceptionEventCreate(
                event_type=req.trigger,
                title=f"manual replan: {req.reason or ''}",
                description=req.reason,
            ),
        )
    # 重新运行工作流（从 plan_generation 开始）
    background_tasks.add_task(_safe_run, task_id)
    return ApiResponse(data={"task_id": task_id, "status": "replanning"})


@router.get("/tasks/{task_id}/report", response_model=ApiResponse[dict])
def get_report(task_id: str, db: Session = Depends(get_db)):
    report = sched_service.get_report(db, task_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not generated yet")
    return ApiResponse(data={
        "task_id": task_id,
        "report_type": report.report_type,
        "content": report.content,
        "metrics": report.metrics,
    })


@router.get("/tasks/{task_id}/exceptions", response_model=ApiResponse[list[ExceptionEventOut]])
def list_exceptions(task_id: str, db: Session = Depends(get_db)):
    items = sched_service.list_exceptions(db, task_id)
    return ApiResponse(data=[ExceptionEventOut.model_validate(e) for e in items])


@router.post("/tasks/{task_id}/exceptions", response_model=ApiResponse[ExceptionEventOut])
def create_exception(task_id: str, payload: ExceptionEventCreate, db: Session = Depends(get_db)):
    event = sched_service.create_exception_event(db, task_id, payload)
    return ApiResponse(data=ExceptionEventOut.model_validate(event))


@router.post("/tasks/{task_id}/execution-feedback", response_model=ApiResponse[dict])
async def execution_feedback(task_id: str, payload: ExecutionFeedback):
    result = await exec_service.receive_execution_feedback(task_id, payload)
    return ApiResponse(data=result)
