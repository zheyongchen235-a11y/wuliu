"""客户端（C 端）schemas：小程序登录、门店、估价、订单、支付。"""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from .common import ORMModel


# ---------------- 登录与用户 ----------------

class WxLoginRequest(BaseModel):
    """小程序登录：wx.login 得到的 code。"""

    code: str
    nickname: str | None = None
    avatar: str | None = None
    gender: int | None = None


class WxUserOut(ORMModel):
    id: str
    openid: str
    nickname: str | None
    avatar: str | None
    gender: int
    phone: str | None
    enabled: bool
    last_login_at: str | None
    created_at: datetime


class WxLoginResponse(BaseModel):
    token: str
    expires_in: int
    user: WxUserOut
    mock_login: bool = False


class WxProfileUpdate(BaseModel):
    nickname: str | None = None
    avatar: str | None = None
    gender: int | None = None
    phone: str | None = None


class WxUserAdminOut(ORMModel):
    id: str
    openid: str
    nickname: str | None
    avatar: str | None
    phone: str | None
    enabled: bool
    last_login_at: str | None
    created_at: datetime
    order_count: int = 0
    total_amount: float = 0.0


# ---------------- 门店与估价 ----------------

class WxStoreOut(ORMModel):
    id: str
    name: str
    address: str | None
    terrain_type: str
    time_window: str
    priority: int
    longitude: float | None
    latitude: float | None


class EstimateRequest(BaseModel):
    store_id: str
    weight: int = Field(gt=0, description="货量(kg)")
    cargo_type: str = "general"
    time_window: str | None = None


class EstimateResponse(BaseModel):
    store_id: str
    store_name: str
    distance_km: float
    amount: float
    breakdown: list[dict]


# ---------------- 订单 ----------------

class OrderCreateRequest(BaseModel):
    store_id: str
    weight: int = Field(gt=0, description="货量(kg)")
    cargo_type: str = "general"
    time_window: str | None = None
    expect_date: date | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    remark: str | None = None


class OrderStatusLogOut(ORMModel):
    id: str
    from_status: str | None
    to_status: str
    operator: str
    remark: str | None
    created_at: datetime


class PaymentOut(ORMModel):
    id: str
    payment_no: str
    order_id: str
    amount: float
    channel: str
    status: str
    transaction_id: str | None
    paid_at: str | None
    created_at: datetime


class OrderOut(ORMModel):
    id: str
    order_no: str
    wx_user_id: str
    store_id: str
    store_name: str | None
    contact_name: str | None
    contact_phone: str | None
    cargo_type: str
    weight: int
    time_window: str
    expect_date: date | None
    distance_km: float
    amount: float
    remark: str | None
    status: str
    task_id: str | None
    plan_id: str | None
    vehicle_id: str | None
    plate: str | None
    vehicle_type: str | None
    driver_id: str | None
    driver_name: str | None
    driver_phone: str | None
    deliver_window: str | None
    estimated_arrival: str | None
    paid_at: str | None
    delivered_at: str | None
    completed_at: str | None
    cancelled_at: str | None
    created_at: datetime
    updated_at: datetime


class OrderDetailOut(OrderOut):
    """订单详情：附带支付流水与状态时间轴。"""

    nickname: str | None = None
    openid: str | None = None
    payments: list[PaymentOut] = Field(default_factory=list)
    status_logs: list[OrderStatusLogOut] = Field(default_factory=list)


# ---------------- 管理端操作 ----------------

class OrderPayRequest(BaseModel):
    channel: str = "wechat_mock"


class OrderScheduleRequest(BaseModel):
    """为订单创建调度任务。"""

    auto_confirm: bool = True
    rule_version: str | None = None


class OrderStatusUpdate(BaseModel):
    status: str
    remark: str | None = None


class OrderCancelRequest(BaseModel):
    reason: str | None = None


class CustomerStatsOut(BaseModel):
    order_total: int = 0
    order_pending_pay: int = 0
    order_paid: int = 0
    order_scheduled: int = 0
    order_completed: int = 0
    order_cancelled: int = 0
    wx_user_total: int = 0
    payment_total_amount: float = 0.0
    payment_today_amount: float = 0.0