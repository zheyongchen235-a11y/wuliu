"""微信小程序登录（code2session + mock 回退）与 C 端用户服务。"""
from __future__ import annotations

import hashlib
import json
import logging
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models.customer import WxUser
from .auth import create_access_token, decode_token

logger = logging.getLogger(__name__)

_JCSCE_URL = "https://api.weixin.qq.com/sns/jscode2session"

_wx_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/wx/login", auto_error=False)


def code2session(code: str) -> dict:
    """用 wx.login 拿到的 code 换取 openid。

    配置了 WX_APP_ID / WX_APP_SECRET 时调用微信官方 jscode2session；
    未配置时（允许 mock）由 code 派生稳定的 openid，便于本地无证书调试。
    """
    appid = settings.wx_app_id
    secret = settings.wx_app_secret
    if not appid or not secret:
        if not settings.wx_mock_login:
            raise HTTPException(status_code=503, detail="未配置微信 AppID/AppSecret，且已禁用 mock 登录")
        digest = hashlib.md5(code.encode("utf-8")).hexdigest()[:16]
        logger.info("微信登录使用 mock 模式，openid=mock_%s", digest)
        return {"openid": f"mock_{digest}", "session_key": None, "unionid": None, "mock": True}

    query = urllib.parse.urlencode(
        {"appid": appid, "secret": secret, "js_code": code, "grant_type": "authorization_code"}
    )
    try:
        with urllib.request.urlopen(f"{_JCSCE_URL}?{query}", timeout=5) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("调用微信 jscode2session 失败：%s", exc)
        raise HTTPException(status_code=502, detail="微信登录服务暂不可用") from exc

    if payload.get("errcode"):
        raise HTTPException(status_code=400, detail=f"微信登录失败：{payload.get('errmsg')}")
    openid = payload.get("openid")
    if not openid:
        raise HTTPException(status_code=400, detail="微信登录失败：未获取到 openid")
    return {
        "openid": openid,
        "session_key": payload.get("session_key"),
        "unionid": payload.get("unionid"),
        "mock": False,
    }


def login_or_register(
    db: Session,
    *,
    code: str,
    nickname: str | None = None,
    avatar: str | None = None,
    gender: int | None = None,
) -> tuple[WxUser, bool]:
    """按 openid 查找用户，不存在则自动注册。返回 (用户, 是否新建, 是否mock)。"""
    info = code2session(code)
    user = db.query(WxUser).filter(WxUser.openid == info["openid"]).first()
    now = datetime.now(timezone.utc).isoformat()
    if user is None:
        user = WxUser(
            openid=info["openid"],
            unionid=info.get("unionid"),
            session_key=info.get("session_key"),
            nickname=nickname or "微信用户",
            avatar=avatar,
            gender=gender or 0,
            enabled=True,
            last_login_at=now,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user, True

    if not user.enabled:
        raise HTTPException(status_code=403, detail="该账号已被禁用，请联系客服")

    if info.get("session_key"):
        user.session_key = info["session_key"]
    if info.get("unionid") and not user.unionid:
        user.unionid = info["unionid"]
    if nickname:
        user.nickname = nickname
    if avatar:
        user.avatar = avatar
    if gender is not None:
        user.gender = gender
    user.last_login_at = now
    db.commit()
    db.refresh(user)
    return user, False


def issue_token(user: WxUser) -> str:
    """签发 C 端访问令牌（scope=wx）。"""
    return create_access_token(user.id, username=user.openid, scope="wx")


def update_profile(db: Session, user: WxUser, payload: dict) -> WxUser:
    """更新 C 端用户资料。"""
    for field in ("nickname", "avatar", "gender", "phone"):
        value = payload.get(field)
        if value is not None:
            setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


def get_current_wx_user(
    token: str | None = Depends(_wx_scheme),
    db: Session = Depends(get_db),
) -> WxUser:
    """FastAPI 依赖：解析 C 端令牌得到当前小程序用户。"""
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="未登录或登录已过期",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise cred_exc
    payload = decode_token(token)
    if not payload or payload.get("type") != "access" or payload.get("scope") != "wx":
        raise cred_exc
    user_id = payload.get("sub")
    if not user_id:
        raise cred_exc
    user = db.get(WxUser, user_id)
    if not user or not user.enabled:
        raise cred_exc
    return user


def get_current_wx_user_id(user: WxUser = Depends(get_current_wx_user)) -> str:
    return user.id