"""管理端客户模块 API：C 端用户、客户订单、支付流水。

需 RBAC 权限：business:customer:list / business:order:list /
business:order:update / business:payment:list
"""
from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import SessionLocal, get_db
from ..models.customer import WxUser
from ..models.rbac import User
from ..schemas.common import ApiResponse, Page
from ..schemas.customer import (
    CustomerStatsOut,
    OrderCancelRequest,
    OrderDetailOut,
    OrderOut,
    OrderScheduleRequest,
    OrderStatusLogOut,
    OrderStatusUpdate,
    PaymentOut,
    WxUserAdminOut,
)
from ..schemas.scheduling import ConfirmRequest, CreateTaskRequest
from ..services import order as order_service
from ..services import scheduling as sched_service
from ..services.auth import require_permissions

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/customer", tags=["客户端管理"])


def _detail_out(order, wx_user: WxUser | None) -> OrderDetailOut:
    base = OrderOut.model_validate(order).model_dump()
    return OrderDetailOut(
        **base,
        nickname=wx_user.nickname if wx_user else None,
        openid=wx_user.openid if wx_user else None,
        payments=[PaymentOut.model_validate(p) for p in order.payments],
        status_logs=[OrderStatusLogOut.model_validate(s) for s in order.status_logs],
    )


# ---------------- 概览 ----------------

@router.get("/stats", response_model=ApiResponse[CustomerStatsOut])
def stats(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permissions("business:order:list")),
):
    return ApiResponse(data=CustomerStatsOut(**order_service.get_stats(db)))


# ---------------- C 端用户 ----------------

@router.get("/wx-users", response_model=ApiResponse[Page[WxUserAdminOut]])
def list_wx_users(
    keyword: str | None = None,
    enabled: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permissions("business:customer:list")),
):
    items, total = order_service.list_wx_users(
        db, keyword=keyword, enabled=enabled, limit=page_size, offset=(page - 1) * page_size
    )
    return ApiResponse(
        data=Page[WxUserAdminOut](
            items=[WxUserAdminOut(**item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.put("/wx-users/{user_id}", response_model=ApiResponse[WxUserAdminOut])
def update_wx_user(
    user_id: str,
    enabled: bool,
    remark: str | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permissions("business:customer:list")),
):
    wx_user = db.get(WxUser, user_id)
    if wx_user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    wx_user.enabled = enabled
    if remark is not None:
        wx_user.remark = remark
    db.commit()
    db.refresh(wx_user)
    data = {
        "id": wx_user.id,
        "openid": wx_user.openid,
        "nickname": wx_user.nickname,
        "avatar": wx_user.avatar,
        "phone": wx_user.phone,
        "enabled": wx_user.enabled,
        "last_login_at": wx_user.last_login_at,
        "created_at": wx_user.created_at,
        "order_count": 0,
        "total_amount": 0.0,
    }
    return ApiResponse(data=WxUserAdminOut(**data), message="已更新")


# ---------------- 订单 ----------------

@router.get("/orders", response_model=ApiResponse[Page[OrderOut]])
def list_orders(
    status: str | None = None,
    store_id: str | None = None,
    keyword: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permissions("business:order:list")),
):
    items, total = order_service.list_orders(
        db,
        status=status,
        store_id=store_id,
        keyword=keyword,
        start_date=start_date,
        end_date=end_date,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    return ApiResponse(
        data=Page[OrderOut](
            items=[OrderOut.model_validate(o) for o in items],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.get("/orders/{order_id}", response_model=ApiResponse[OrderDetailOut])
def get_order(
    order_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permissions("business:order:list")),
):
    order = order_service.get_order_detail(db, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="订单不存在")
    wx_user = db.get(WxUser, order.wx_user_id)
    return ApiResponse(data=_detail_out(order, wx_user))


@router.post("/orders/{order_id}/schedule", response_model=ApiResponse[dict])
def schedule_order(
    order_id: str,
    payload: OrderScheduleRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permissions("business:order:update")),
):
    """为订单创建调度任务，工作流跑完后自动把车辆/司机回填到订单。"""
    order = order_service.get_order(db, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status != "paid":
        raise HTTPException(status_code=400, detail="仅「已支付待调度」的订单可以创建调度任务")

    task = sched_service.create_task(
        db,
        CreateTaskRequest(
            schedule_date=order.expect_date or date.today(),
            time_window=order.time_window if order.time_window in ("AM", "PM") else "all",
            rule_version=payload.rule_version,
            extra={
                "source": "wx_order",
                "order_ids": [order.id],
                "demand_overrides": {order.store_id: order.weight},
            },
        ),
    )
    background_tasks.add_task(_run_and_bind, task.id, [order.id], payload.auto_confirm)
    return ApiResponse(
        data={"task_id": task.id, "order_id": order.id, "auto_confirm": payload.auto_confirm},
        message="已创建调度任务，正在生成方案",
    )


async def _run_and_bind(task_id: str, order_ids: list[str], auto_confirm: bool) -> None:
    """后台：跑调度工作流 → 回填订单 → （可选）自动确认最优方案。"""
    from ..workflow.graph import resume_scheduling, run_scheduling

    try:
        await run_scheduling(task_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("订单调度任务 %s 运行失败: %s", task_id, exc)
        with SessionLocal() as db:
            sched_service.update_task_status(db, task_id, status="failed", error_message=str(exc))
        return

    with SessionLocal() as db:
        result = order_service.bind_orders_to_plan(db, task_id, order_ids)
    logger.info("订单回填结果：%s", result)

    plan_id = result.get("plan_id")
    if not auto_confirm or not plan_id:
        return

    with SessionLocal() as db:
        sched_service.confirm_plan(
            db,
            task_id,
            ConfirmRequest(
                approved=True,
                plan_id=plan_id,
                operator="系统自动确认",
                comment="客户订单调度自动确认最优方案",
            ),
        )
    try:
        await resume_scheduling(task_id, {"approved": True, "plan_id": plan_id})
    except Exception as exc:  # noqa: BLE001
        logger.exception("订单调度任务 %s 自动确认失败: %s", task_id, exc)


@router.put("/orders/{order_id}/status", response_model=ApiResponse[OrderOut])
def update_order_status(
    order_id: str,
    payload: OrderStatusUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permissions("business:order:update")),
):
    order = order_service.get_order(db, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="订单不存在")
    order_service.update_status_by_admin(db, order, payload.status, remark=payload.remark)
    return ApiResponse(data=OrderOut.model_validate(order), message="状态已更新")


@router.post("/orders/{order_id}/cancel", response_model=ApiResponse[OrderOut])
def cancel_order(
    order_id: str,
    payload: OrderCancelRequest | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permissions("business:order:update")),
):
    order = order_service.get_order(db, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="订单不存在")
    reason = (payload.reason if payload else None) or "管理员取消订单"
    order_service.cancel_order(db, order, operator="admin", reason=reason)
    return ApiResponse(data=OrderOut.model_validate(order), message="订单已取消")


# ---------------- 支付流水 ----------------

@router.get("/payments", response_model=ApiResponse[Page[PaymentOut]])
def list_payments(
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permissions("business:payment:list")),
):
    items, total = order_service.list_payments(
        db, status=status, limit=page_size, offset=(page - 1) * page_size
    )
    return ApiResponse(
        data=Page[PaymentOut](
            items=[PaymentOut.model_validate(p) for p in items],
            total=total,
            page=page,
            page_size=page_size,
        )
    )