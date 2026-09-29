"""客户端（C 端）模型：小程序用户、客户订单、模拟支付流水、订单状态日志。"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, GUID, TimestampMixin


class WxUser(Base, TimestampMixin):
    """微信小程序用户（C 端用户，独立于 RBAC 用户体系）。"""

    __tablename__ = "wx_user"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=GUID.default)
    openid: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, comment="微信 openid")
    unionid: Mapped[str | None] = mapped_column(String(128), comment="微信 unionid")
    session_key: Mapped[str | None] = mapped_column(String(128), comment="会话密钥（真实模式写入）")
    nickname: Mapped[str | None] = mapped_column(String(128))
    avatar: Mapped[str | None] = mapped_column(String(512))
    gender: Mapped[int] = mapped_column(Integer, default=0, comment="0 未知 / 1 男 / 2 女")
    phone: Mapped[str | None] = mapped_column(String(32))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[str | None] = mapped_column(String(64))
    remark: Mapped[str | None] = mapped_column(String(256))

    orders: Mapped[list["CustomerOrder"]] = relationship(
        "CustomerOrder", back_populates="wx_user"
    )


class CustomerOrder(Base, TimestampMixin):
    """客户订单：C 端下单，管理端调度后回填车辆与司机。"""

    __tablename__ = "customer_order"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=GUID.default)
    order_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, comment="订单号")
    wx_user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("wx_user.id", ondelete="CASCADE"), nullable=False
    )
    store_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("store.id", ondelete="CASCADE"), nullable=False
    )
    store_name: Mapped[str | None] = mapped_column(String(128), comment="门店名称快照")
    contact_name: Mapped[str | None] = mapped_column(String(64))
    contact_phone: Mapped[str | None] = mapped_column(String(32))
    cargo_type: Mapped[str] = mapped_column(String(32), default="general", comment="货物类型")
    weight: Mapped[int] = mapped_column(Integer, default=0, comment="货量(kg)")
    time_window: Mapped[str] = mapped_column(String(16), default="any", comment="AM / PM / any")
    expect_date: Mapped[date | None] = mapped_column(Date, comment="期望配送日期")
    distance_km: Mapped[float] = mapped_column(Float, default=0.0)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, comment="应付金额(元)")
    remark: Mapped[str | None] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(
        String(16), default="pending_pay",
        comment="pending_pay / paid / scheduled / delivering / delivered / completed / cancelled",
    )

    # ---- 调度结果回填 ----
    task_id: Mapped[str | None] = mapped_column(String(64), comment="关联调度任务")
    plan_id: Mapped[str | None] = mapped_column(String(32), comment="采纳方案编号")
    vehicle_id: Mapped[str | None] = mapped_column(String(64))
    plate: Mapped[str | None] = mapped_column(String(32))
    vehicle_type: Mapped[str | None] = mapped_column(String(32))
    driver_id: Mapped[str | None] = mapped_column(String(64))
    driver_name: Mapped[str | None] = mapped_column(String(64))
    driver_phone: Mapped[str | None] = mapped_column(String(32))
    deliver_window: Mapped[str | None] = mapped_column(String(16), comment="实际配送时段")
    estimated_arrival: Mapped[str | None] = mapped_column(String(64))

    # ---- 时间戳 ----
    paid_at: Mapped[str | None] = mapped_column(String(64))
    delivered_at: Mapped[str | None] = mapped_column(String(64))
    completed_at: Mapped[str | None] = mapped_column(String(64))
    cancelled_at: Mapped[str | None] = mapped_column(String(64))

    wx_user: Mapped["WxUser"] = relationship("WxUser", back_populates="orders")
    payments: Mapped[list["PaymentRecord"]] = relationship(
        "PaymentRecord", back_populates="order", cascade="all, delete-orphan"
    )
    status_logs: Mapped[list["OrderStatusLog"]] = relationship(
        "OrderStatusLog", back_populates="order", cascade="all, delete-orphan"
    )


class PaymentRecord(Base, TimestampMixin):
    """模拟支付流水。"""

    __tablename__ = "payment_record"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=GUID.default)
    payment_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, comment="支付流水号")
    order_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("customer_order.id", ondelete="CASCADE"), nullable=False
    )
    wx_user_id: Mapped[str | None] = mapped_column(String(64))
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    channel: Mapped[str] = mapped_column(String(32), default="wechat_mock", comment="支付渠道(模拟)")
    status: Mapped[str] = mapped_column(
        String(16), default="success", comment="pending / success / failed / refunded"
    )
    transaction_id: Mapped[str | None] = mapped_column(String(64), comment="模拟第三方流水号")
    paid_at: Mapped[str | None] = mapped_column(String(64))
    remark: Mapped[str | None] = mapped_column(String(256))

    order: Mapped["CustomerOrder"] = relationship("CustomerOrder", back_populates="payments")


class OrderStatusLog(Base, TimestampMixin):
    """订单状态流转日志（小程序详情页时间轴数据源）。"""

    __tablename__ = "order_status_log"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=GUID.default)
    order_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("customer_order.id", ondelete="CASCADE"), nullable=False
    )
    from_status: Mapped[str | None] = mapped_column(String(16))
    to_status: Mapped[str] = mapped_column(String(16), nullable=False)
    operator: Mapped[str] = mapped_column(String(16), default="system", comment="user / admin / system")
    remark: Mapped[str | None] = mapped_column(String(256))

    order: Mapped["CustomerOrder"] = relationship("CustomerOrder", back_populates="status_logs")