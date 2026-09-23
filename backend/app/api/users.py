"""用户管理 API：CRUD + 重置密码 + 分配角色。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.rbac import Role, User, UserRole
from ..schemas.common import ApiResponse, Page
from ..schemas.rbac import (
    UserCreate,
    UserOut,
    UserResetPassword,
    UserUpdate,
)
from ..services.auth import (
    get_current_user,
    hash_password,
    require_permissions,
    verify_password,
)

router = APIRouter(prefix="/api/v1/users", tags=["用户管理"])


def _to_out(u: User) -> UserOut:
    return UserOut(
        id=u.id,
        username=u.username,
        nickname=u.nickname,
        email=u.email,
        phone=u.phone,
        avatar=u.avatar,
        dept_id=u.dept_id,
        is_super=u.is_super,
        enabled=u.enabled,
        last_login_at=u.last_login_at,
        role_ids=[r.id for r in u.roles],
        role_codes=[r.code for r in u.roles],
        dept_name=u.dept.name if u.dept else None,
    )


@router.get("", response_model=ApiResponse[Page[UserOut]])
def list_users(
    keyword: str | None = Query(None),
    dept_id: str | None = Query(None),
    enabled: bool | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _=Depends(require_permissions("system:user:list")),
):
    q = db.query(User)
    if keyword:
        kw = f"%{keyword}%"
        q = q.filter(or_(User.username.like(kw), User.nickname.like(kw), User.email.like(kw)))
    if dept_id:
        q = q.filter(User.dept_id == dept_id)
    if enabled is not None:
        q = q.filter(User.enabled == enabled)
    total = q.count()
    rows = q.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return ApiResponse(
        data=Page(
            items=[_to_out(u) for u in rows],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.post("", response_model=ApiResponse[UserOut])
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _=Depends(require_permissions("system:user:create")),
):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(400, "用户名已存在")
    user = User(
        username=payload.username,
        nickname=payload.nickname,
        email=payload.email,
        phone=payload.phone,
        dept_id=payload.dept_id,
        is_super=payload.is_super,
        enabled=payload.enabled,
        hashed_password=hash_password(payload.password),
    )
    if payload.role_ids:
        user.roles = db.query(Role).filter(Role.id.in_(payload.role_ids)).all()
    db.add(user)
    db.commit()
    db.refresh(user)
    return ApiResponse(data=_to_out(user))


@router.put("/{user_id}", response_model=ApiResponse[UserOut])
def update_user(
    user_id: str,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_permissions("system:user:update")),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "用户不存在")
    data = payload.model_dump(exclude_unset=True)
    role_ids = data.pop("role_ids", None)
    for k, v in data.items():
        setattr(user, k, v)
    if role_ids is not None:
        user.roles = db.query(Role).filter(Role.id.in_(role_ids)).all()
    db.commit()
    db.refresh(user)
    return ApiResponse(data=_to_out(user))


@router.delete("/{user_id}", response_model=ApiResponse[dict])
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
    _=Depends(require_permissions("system:user:delete")),
):
    if current.id == user_id:
        raise HTTPException(400, "不能删除当前登录用户")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "用户不存在")
    if user.is_super and user.username == "admin":
        raise HTTPException(400, "内置超级管理员不可删除")
    db.delete(user)
    db.commit()
    return ApiResponse(data={"ok": True})


@router.put("/{user_id}/password/reset", response_model=ApiResponse[dict])
def reset_user_password(
    user_id: str,
    payload: UserResetPassword,
    db: Session = Depends(get_db),
    _=Depends(require_permissions("system:user:reset")),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "用户不存在")
    user.hashed_password = hash_password(payload.new_password)
    db.commit()
    return ApiResponse(data={"ok": True})
