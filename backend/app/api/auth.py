"""认证 API：登录/登出/刷新/当前用户/修改密码。"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.rbac import User
from ..schemas.common import ApiResponse
from ..schemas.rbac import (
    LoginRequest,
    PasswordChange,
    TokenResponse,
    UserCreate,
    UserInfo,
    UserOut,
)
from ..services.auth import (
    authenticate,
    build_user_info,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    hash_password,
)

router = APIRouter(prefix="/api/v1/auth", tags=["认证"])


@router.post("/login", response_model=ApiResponse[TokenResponse])
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate(db, payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    user.last_login_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    access = create_access_token(user.id, username=user.username)
    refresh = create_refresh_token(user.id, username=user.username)
    return ApiResponse(
        data=TokenResponse(
            access_token=access,
            refresh_token=refresh,
            expires_in=60 * 60 * 12,
        )
    )


@router.post("/refresh", response_model=ApiResponse[TokenResponse])
def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="refresh token 无效")
    user = db.get(User, payload.get("sub"))
    if not user or not user.enabled:
        raise HTTPException(status_code=401, detail="用户不可用")
    return ApiResponse(
        data=TokenResponse(
            access_token=create_access_token(user.id, username=user.username),
            refresh_token=create_refresh_token(user.id, username=user.username),
            expires_in=60 * 60 * 12,
        )
    )


@router.post("/logout", response_model=ApiResponse[dict])
def logout(user: User = Depends(get_current_user)):
    # JWT 无服务端会话，直接由前端丢弃令牌即可
    return ApiResponse(data={"ok": True})


@router.get("/me", response_model=ApiResponse[UserInfo])
def current_user_info(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    info = build_user_info(db, user)
    return ApiResponse(data=UserInfo.model_validate(info))


@router.put("/password", response_model=ApiResponse[dict])
def change_my_password(
    payload: PasswordChange,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from ..services.auth import verify_password

    if not verify_password(payload.old_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="原密码错误")
    user.hashed_password = hash_password(payload.new_password)
    db.commit()
    return ApiResponse(data={"ok": True})
