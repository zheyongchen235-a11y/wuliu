"""客户订单服务：估价、下单、模拟支付、状态流转、调度结果回填。"""
from __future__ import annotations

import logging
import math
import random
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..models.basic import Driver, Store, Vehicle
from ..models.customer import CustomerOrder, OrderStatusLog, PaymentRecord, WxUser
from . import scheduling as sched_service

logger = logging.getLogger(__name__)

# ---------- 计价参数 ----------
# 仓库中心点（用于估算配送距离）
WAREHOUSE_CENTER = (39.909, 116.397)  # (lat, lon)
BASE_FEE = 15.0            # 基础运费
PER_100KG_FEE = 8.0        # 每 100kg 计费
PER_KM_FEE = 2.0           # 每公里计费
AM_SURCHARGE = 5.0         # 上午时段附加

CARGO_TYPES = {
    "general": "普通货物",
    "fresh": "生鲜冷链",
    "fragile": "易碎品",
    "bulk": "大宗货物",
}

# 合法状态流转关系
_STATUS_FLOW = {
    "pending_pay": ["paid", "cancelled"],
    "paid": ["scheduled", "cancelled"],
    "scheduled": ["delivering", "delivered", "completed", "cancelled"],
    "delivering": ["delivered", "completed"],
    "delivered": ["completed"],
    "completed": [],
    "cancelled": [],
}

STATUS_LABELS = {
    "pending_pay": "待支付",
    "paid": "已支付待调度",
    "scheduled": "已排车",
    "delivering": "配送中",
    "delivered": "已送达",
    "completed": "已完成",
    "cancelled": "已取消",
}

# 状态时间轴排序权重（created_at 精度为秒，同秒内按业务顺序稳定展示）
_STATUS_SEQ = {
    "pending_pay": 0,
    "paid": 1,
    "scheduled": 2,
    "delivering": 3,
    "delivered": 4,
    "completed": 5,
    "cancelled": 6,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fnum(value: Decimal | float | None) -> float:
    if value is None:
        return 0.0
    return float(value)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """两点球面距离（公里）。"""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(2 * r * math.asin(math.sqrt(a)), 2)


def _gen_no(prefix: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{prefix}{stamp}{random.randint(1000, 9999)}"


def calc_estimate(store: Store, weight: int, time_window: str | None = None) -> dict:
    """计算配送距离与费用明细。"""
    lat = store.latitude if store.latitude is not None else WAREHOUSE_CENTER[0]
    lon = store.longitude if store.longitude is not None else WAREHOUSE_CENTER[1]
    distance_km = _haversine_km(WAREHOUSE_CENTER[0], WAREHOUSE_CENTER[1], lat, lon)

    weight_fee = math.ceil(max(weight, 0) / 100) * PER_100KG_FEE
    distance_fee = round(distance_km * PER_KM_FEE, 2)
    window = _effective_window(store, time_window)
    time_fee = AM_SURCHARGE if window == "AM" else 0.0

    total = BASE_FEE + weight_fee + distance_fee + time_fee
    amount = Decimal(str(total)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return {
        "distance_km": distance_km,
        "amount": amount,
        "time_window": window,
        "breakdown": [
            {"label": "基础运费", "amount": BASE_FEE},
            {"label": f"货量费（{weight}kg）", "amount": weight_fee},
            {"label": f"距离费（{distance_km}km）", "amount": distance_fee},
            {"label": "上午时段附加", "amount": time_fee},
        ],
    }


def _effective_window(store: Store, requested: str | None = None) -> str:
    """配送时段以门店约束为准：门店为 AM/PM 时强制跟随，门店不限时采用用户选择（默认 AM）。"""
    store_window = (store.time_window or "any").upper()
    if store_window in ("AM", "PM"):
        return store_window
    if requested and requested.upper() in ("AM", "PM"):
        return requested.upper()
    return "AM"


def _log_status(
    db: Session,
    order: CustomerOrder,
    from_status: str | None,
    to_status: str,
    *,
    operator: str = "system",
    remark: str | None = None,
) -> None:
    db.add(
        OrderStatusLog(
            order_id=order.id,
            from_status=from_status,
            to_status=to_status,
            operator=operator,
            remark=remark,
        )
    )


def _transition(
    db: Session,
    order: CustomerOrder,
    to_status: str,
    *,
    operator: str = "system",
    remark: str | None = None,
) -> CustomerOrder:
    """执行状态流转（含合法性校验与日志）。"""
    allowed = _STATUS_FLOW.get(order.status, [])
    if to_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"订单当前状态为「{STATUS_LABELS.get(order.status, order.status)}」，不能变更为「{STATUS_LABELS.get(to_status, to_status)}」",
        )
    from_status = order.status
    order.status = to_status
    stamp = _now()
    if to_status == "paid":
        order.paid_at = stamp
    elif to_status == "delivered":
        order.delivered_at = stamp
    elif to_status == "completed":
        order.completed_at = stamp
    elif to_status == "cancelled":
        order.cancelled_at = stamp
    _log_status(db, order, from_status, to_status, operator=operator, remark=remark)
    return order


# ---------------- 下单 ----------------

def create_order(db: Session, user: WxUser, payload: dict) -> CustomerOrder:
    store = db.get(Store, payload["store_id"])
    if store is None or not store.enabled:
        raise HTTPException(status_code=404, detail="门店不存在或已停用")

    weight = int(payload["weight"])
    estimate = calc_estimate(store, weight, payload.get("time_window"))
    order = CustomerOrder(
        order_no=_gen_no("SO"),
        wx_user_id=user.id,
        store_id=store.id,
        store_name=store.name,
        contact_name=payload.get("contact_name") or user.nickname,
        contact_phone=payload.get("contact_phone") or user.phone,
        cargo_type=payload.get("cargo_type") or "general",
        weight=weight,
        time_window=estimate["time_window"],
        expect_date=payload.get("expect_date") or date.today(),
        distance_km=estimate["distance_km"],
        amount=estimate["amount"],
        remark=payload.get("remark"),
        status="pending_pay",
    )
    db.add(order)
    db.flush()
    _log_status(db, order, None, "pending_pay", operator="user", remark="用户提交订单")
    db.commit()
    db.refresh(order)
    return order


def get_order(db: Session, order_id: str) -> CustomerOrder | None:
    return db.get(CustomerOrder, order_id)


def get_order_detail(db: Session, order_id: str) -> CustomerOrder | None:
    order = db.scalar(
        select(CustomerOrder)
        .where(CustomerOrder.id == order_id)
        .options(
            selectinload(CustomerOrder.payments),
            selectinload(CustomerOrder.status_logs),
        )
    )
    if order is None:
        return None
    # created_at 为秒级精度，同秒事件按业务顺序稳定排序，保证时间轴正序展示
    order.status_logs.sort(key=lambda s: (_STATUS_SEQ.get(s.to_status, 99), s.created_at or ""))
    order.payments.sort(key=lambda p: p.created_at or "")
    return order


def list_orders(
    db: Session,
    *,
    wx_user_id: str | None = None,
    status: str | None = None,
    store_id: str | None = None,
    keyword: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[CustomerOrder], int]:
    stmt = select(CustomerOrder)
    count_stmt = select(func.count(CustomerOrder.id))
    conditions = []
    if wx_user_id:
        conditions.append(CustomerOrder.wx_user_id == wx_user_id)
    if status:
        conditions.append(CustomerOrder.status == status)
    if store_id:
        conditions.append(CustomerOrder.store_id == store_id)
    if keyword:
        like = f"%{keyword}%"
        conditions.append(
            (CustomerOrder.order_no.like(like))
            | (CustomerOrder.store_name.like(like))
            | (CustomerOrder.contact_phone.like(like))
        )
    if start_date:
        conditions.append(func.date(CustomerOrder.created_at) >= start_date)
    if end_date:
        conditions.append(func.date(CustomerOrder.created_at) <= end_date)
    for cond in conditions:
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)
    stmt = stmt.order_by(CustomerOrder.created_at.desc()).limit(limit).offset(offset)
    items = list(db.scalars(stmt))
    total = int(db.scalar(count_stmt) or 0)
    return items, total


# ---------------- 支付（模拟） ----------------

def pay_order(db: Session, order: CustomerOrder, channel: str = "wechat_mock") -> PaymentRecord:
    if order.status != "pending_pay":
        raise HTTPException(status_code=400, detail="订单当前状态不可支付")

    payment = PaymentRecord(
        payment_no=_gen_no("PAY"),
        order_id=order.id,
        wx_user_id=order.wx_user_id,
        amount=order.amount,
        channel=channel or "wechat_mock",
        status="success",
        transaction_id=f"MOCK{random.randint(10**11, 10**12 - 1)}",
        paid_at=_now(),
        remark="模拟支付成功",
    )
    db.add(payment)
    db.flush()
    _transition(db, order, "paid", operator="user", remark=f"模拟支付 ¥{_fnum(order.amount):.2f}")
    db.commit()
    db.refresh(payment)
    return payment


def cancel_order(db: Session, order: CustomerOrder, *, operator: str = "user", reason: str | None = None) -> CustomerOrder:
    _transition(db, order, "cancelled", operator=operator, remark=reason or "订单取消")
    db.commit()
    db.refresh(order)
    return order


def confirm_order(db: Session, order: CustomerOrder) -> CustomerOrder:
    if order.status not in ("scheduled", "delivering", "delivered"):
        raise HTTPException(status_code=400, detail="当前状态不可确认收货")
    _transition(db, order, "completed", operator="user", remark="用户确认收货")
    db.commit()
    db.refresh(order)
    return order


def update_status_by_admin(
    db: Session,
    order: CustomerOrder,
    to_status: str,
    *,
    remark: str | None = None,
) -> CustomerOrder:
    if to_status not in _STATUS_FLOW:
        raise HTTPException(status_code=400, detail=f"未知状态：{to_status}")
    if to_status == "cancelled":
        _transition(db, order, "cancelled", operator="admin", remark=remark or "管理员取消订单")
    else:
        _transition(db, order, to_status, operator="admin", remark=remark or "管理员更新状态")
    db.commit()
    db.refresh(order)
    return order


# ---------------- 调度结果回填 ----------------

def _estimate_arrival(time_window: str | None, base: date | None = None) -> str:
    day = base or date.today()
    hour = 18 if (time_window or "AM").upper() == "PM" else 12
    return datetime.combine(day, datetime.min.time()).replace(hour=hour).strftime("%Y-%m-%d %H:%M")


def bind_orders_to_plan(db: Session, task_id: str, order_ids: list[str]) -> dict:
    """把调度任务的最优方案回填到订单上（车辆 / 司机 / 时段）。"""
    plans = sched_service.list_plans(db, task_id)
    if not plans:
        return {"bound": 0, "task_id": task_id, "reason": "该任务暂无候选方案"}

    best = max(plans, key=lambda p: (p.score.total_score if p.score else 0.0))
    bound = 0
    for order_id in order_ids:
        order = db.get(CustomerOrder, order_id)
        if order is None:
            continue
        detail = None
        for d in best.details:
            if order.store_id in (d.store_ids or []):
                detail = d
                break
        if detail is None:
            logger.warning("任务 %s 方案 %s 未覆盖门店 %s", task_id, best.plan_id, order.store_id)
            _log_status(
                db, order, order.status, order.status, operator="system",
                remark=f"方案 {best.plan_id} 未覆盖该门店，等待下次调度",
            )
            continue

        vehicle = db.get(Vehicle, detail.vehicle_id)
        driver = db.get(Driver, vehicle.driver_id) if vehicle and vehicle.driver_id else None
        from_status = order.status
        order.task_id = task_id
        order.plan_id = best.plan_id
        order.vehicle_id = detail.vehicle_id
        order.vehicle_type = detail.vehicle_type
        order.plate = vehicle.plate if vehicle else None
        order.driver_id = vehicle.driver_id if vehicle else None
        order.driver_name = driver.name if driver else None
        order.driver_phone = driver.phone if driver else None
        order.deliver_window = detail.time_window
        order.estimated_arrival = _estimate_arrival(detail.time_window, order.expect_date)
        order.status = "scheduled"
        _log_status(
            db, order, from_status, "scheduled", operator="system",
            remark=f"已排车：{order.plate or detail.vehicle_id}（方案 {best.plan_id}）",
        )
        bound += 1

    db.commit()
    return {"bound": bound, "task_id": task_id, "plan_id": best.plan_id, "total_orders": len(order_ids)}


# ---------------- 统计 ----------------

def get_stats(db: Session) -> dict:
    def _count(status: str | None = None) -> int:
        stmt = select(func.count(CustomerOrder.id))
        if status:
            stmt = stmt.where(CustomerOrder.status == status)
        return int(db.scalar(stmt) or 0)

    total_amount = db.scalar(
        select(func.coalesce(func.sum(PaymentRecord.amount), 0)).where(PaymentRecord.status == "success")
    )
    today = date.today()
    today_amount = db.scalar(
        select(func.coalesce(func.sum(PaymentRecord.amount), 0)).where(
            PaymentRecord.status == "success",
            func.date(PaymentRecord.created_at) == today,
        )
    )
    return {
        "order_total": _count(),
        "order_pending_pay": _count("pending_pay"),
        "order_paid": _count("paid"),
        "order_scheduled": _count("scheduled"),
        "order_completed": _count("completed"),
        "order_cancelled": _count("cancelled"),
        "wx_user_total": int(db.scalar(select(func.count(WxUser.id))) or 0),
        "payment_total_amount": _fnum(total_amount),
        "payment_today_amount": _fnum(today_amount),
    }


def list_payments(
    db: Session,
    *,
    wx_user_id: str | None = None,
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[PaymentRecord], int]:
    stmt = select(PaymentRecord)
    count_stmt = select(func.count(PaymentRecord.id))
    conditions = []
    if wx_user_id:
        conditions.append(PaymentRecord.wx_user_id == wx_user_id)
    if status:
        conditions.append(PaymentRecord.status == status)
    for cond in conditions:
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)
    stmt = stmt.order_by(PaymentRecord.created_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(stmt)), int(db.scalar(count_stmt) or 0)


def list_wx_users(
    db: Session,
    *,
    keyword: str | None = None,
    enabled: bool | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """C 端用户列表（附带订单数与累计金额）。"""
    stmt = select(WxUser)
    count_stmt = select(func.count(WxUser.id))
    if keyword:
        like = f"%{keyword}%"
        cond = (WxUser.nickname.like(like)) | (WxUser.openid.like(like)) | (WxUser.phone.like(like))
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)
    if enabled is not None:
        stmt = stmt.where(WxUser.enabled == enabled)
        count_stmt = count_stmt.where(WxUser.enabled == enabled)
    stmt = stmt.order_by(WxUser.created_at.desc()).limit(limit).offset(offset)
    users = list(db.scalars(stmt))
    total = int(db.scalar(count_stmt) or 0)

    user_ids = [u.id for u in users]
    counts: dict[str, int] = {}
    amounts: dict[str, float] = {}
    if user_ids:
        rows = db.execute(
            select(CustomerOrder.wx_user_id, func.count(CustomerOrder.id))
            .where(CustomerOrder.wx_user_id.in_(user_ids))
            .group_by(CustomerOrder.wx_user_id)
        ).all()
        counts = {r[0]: int(r[1]) for r in rows}
        rows = db.execute(
            select(CustomerOrder.wx_user_id, func.coalesce(func.sum(CustomerOrder.amount), 0))
            .where(CustomerOrder.wx_user_id.in_(user_ids), CustomerOrder.status != "cancelled")
            .group_by(CustomerOrder.wx_user_id)
        ).all()
        amounts = {r[0]: _fnum(r[1]) for r in rows}

    items = []
    for u in users:
        data = {
            "id": u.id,
            "openid": u.openid,
            "nickname": u.nickname,
            "avatar": u.avatar,
            "phone": u.phone,
            "enabled": u.enabled,
            "last_login_at": u.last_login_at,
            "created_at": u.created_at,
            "order_count": counts.get(u.id, 0),
            "total_amount": amounts.get(u.id, 0.0),
        }
        items.append(data)
    return items, total