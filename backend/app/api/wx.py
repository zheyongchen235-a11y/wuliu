"""小程序（C 端）API：微信登录、门店、估价、下单、模拟支付。

除 /login 外均需携带 C 端令牌（scope=wx）。
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.basic import Store
from ..models.customer import WxUser
from ..schemas.common import ApiResponse, Page
from ..schemas.customer import (
    EstimateRequest,
    EstimateResponse,
    OrderCreateRequest,
    OrderDetailOut,
    OrderOut,
    OrderPayRequest,
    OrderStatusLogOut,
    PaymentOut,
    WxLoginRequest,
    WxLoginResponse,
    WxProfileUpdate,
    WxStoreOut,
    WxUserOut,
)
from ..services import order as order_service
from ..services import wx as wx_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/wx", tags=["小程序端"])


# ---------------- 登录与资料 ----------------

@router.post("/login", response_model=ApiResponse[WxLoginResponse])
def login(payload: WxLoginRequest, db: Session = Depends(get_db)):
    """微信登录：前端 wx.login 拿到的 code 换取令牌，首次登录自动注册。"""
    user, created = wx_service.login_or_register(
        db,
        code=payload.code,
        nickname=payload.nickname,
        avatar=payload.avatar,
        gender=payload.gender,
    )
    token = wx_service.issue_token(user)
    return ApiResponse(
        data=WxLoginResponse(
            token=token,
            expires_in=60 * 60 * 12,
            user=WxUserOut.model_validate(user),
            mock_login=not bool(wx_service.settings.wx_app_id),
        ),
        message="登录成功" if not created else "登录成功，已自动注册",
    )


@router.get("/profile", response_model=ApiResponse[WxUserOut])
def profile(user: WxUser = Depends(wx_service.get_current_wx_user)):
    return ApiResponse(data=WxUserOut.model_validate(user))


@router.put("/profile", response_model=ApiResponse[WxUserOut])
def update_profile(
    payload: WxProfileUpdate,
    user: WxUser = Depends(wx_service.get_current_wx_user),
    db: Session = Depends(get_db),
):
    updated = wx_service.update_profile(db, user, payload.model_dump(exclude_unset=True))
    return ApiResponse(data=WxUserOut.model_validate(updated))


# ---------------- 门店与估价 ----------------

@router.get("/stores", response_model=ApiResponse[list[WxStoreOut]])
def list_stores(db: Session = Depends(get_db)):
    stores = list(db.scalars(select(Store).where(Store.enabled.is_(True)).order_by(Store.id)))
    return ApiResponse(data=[WxStoreOut.model_validate(s) for s in stores])


@router.post("/estimate", response_model=ApiResponse[EstimateResponse])
def estimate(payload: EstimateRequest, db: Session = Depends(get_db)):
    store = db.get(Store, payload.store_id)
    if store is None or not store.enabled:
        raise HTTPException(status_code=404, detail="门店不存在或已停用")
    result = order_service.calc_estimate(store, payload.weight, payload.time_window)
    return ApiResponse(
        data=EstimateResponse(
            store_id=store.id,
            store_name=store.name,
            distance_km=result["distance_km"],
            amount=float(result["amount"]),
            breakdown=result["breakdown"],
        )
    )


# ---------------- 订单 ----------------

def _detail_out(order, wx_user: WxUser | None) -> OrderDetailOut:
    base = OrderOut.model_validate(order).model_dump()
    return OrderDetailOut(
        **base,
        nickname=wx_user.nickname if wx_user else None,
        openid=wx_user.openid if wx_user else None,
        payments=[PaymentOut.model_validate(p) for p in order.payments],
        status_logs=[OrderStatusLogOut.model_validate(s) for s in order.status_logs],
    )


def _get_own_order(db: Session, order_id: str, user: WxUser):
    order = order_service.get_order_detail(db, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.wx_user_id != user.id:
        raise HTTPException(status_code=403, detail="无权访问该订单")
    return order


@router.post("/orders", response_model=ApiResponse[OrderOut])
def create_order(
    payload: OrderCreateRequest,
    user: WxUser = Depends(wx_service.get_current_wx_user),
    db: Session = Depends(get_db),
):
    order = order_service.create_order(db, user, payload.model_dump())
    return ApiResponse(data=OrderOut.model_validate(order), message="下单成功，请尽快完成支付")


@router.get("/orders", response_model=ApiResponse[Page[OrderOut]])
def list_my_orders(
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    user: WxUser = Depends(wx_service.get_current_wx_user),
    db: Session = Depends(get_db),
):
    items, total = order_service.list_orders(
        db,
        wx_user_id=user.id,
        status=status,
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
def get_my_order(
    order_id: str,
    user: WxUser = Depends(wx_service.get_current_wx_user),
    db: Session = Depends(get_db),
):
    order = _get_own_order(db, order_id, user)
    return ApiResponse(data=_detail_out(order, user))


@router.post("/orders/{order_id}/pay", response_model=ApiResponse[OrderOut])
def pay_order(
    order_id: str,
    payload: OrderPayRequest | None = None,
    user: WxUser = Depends(wx_service.get_current_wx_user),
    db: Session = Depends(get_db),
):
    """模拟支付：直接生成成功的支付流水。"""
    order = _get_own_order(db, order_id, user)
    channel = (payload.channel if payload else None) or "wechat_mock"
    order_service.pay_order(db, order, channel=channel)
    db.refresh(order)
    return ApiResponse(data=OrderOut.model_validate(order), message="支付成功")


@router.post("/orders/{order_id}/cancel", response_model=ApiResponse[OrderOut])
def cancel_order(
    order_id: str,
    user: WxUser = Depends(wx_service.get_current_wx_user),
    db: Session = Depends(get_db),
):
    order = _get_own_order(db, order_id, user)
    order_service.cancel_order(db, order, operator="user")
    return ApiResponse(data=OrderOut.model_validate(order), message="订单已取消")


@router.post("/orders/{order_id}/confirm", response_model=ApiResponse[OrderOut])
def confirm_order(
    order_id: str,
    user: WxUser = Depends(wx_service.get_current_wx_user),
    db: Session = Depends(get_db),
):
    order = _get_own_order(db, order_id, user)
    order_service.confirm_order(db, order)
    return ApiResponse(data=OrderOut.model_validate(order), message="已确认收货")


# ---------------- 支付流水 ----------------

@router.get("/payments", response_model=ApiResponse[Page[PaymentOut]])
def list_my_payments(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    user: WxUser = Depends(wx_service.get_current_wx_user),
    db: Session = Depends(get_db),
):
    items, total = order_service.list_payments(
        db, wx_user_id=user.id, limit=page_size, offset=(page - 1) * page_size
    )
    return ApiResponse(
        data=Page[PaymentOut](
            items=[PaymentOut.model_validate(p) for p in items],
            total=total,
            page=page,
            page_size=page_size,
        )
    )