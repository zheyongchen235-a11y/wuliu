"""认证与授权服务：密码哈希、JWT、当前用户依赖、权限校验。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models.rbac import Menu, Permission, Role, User


# ---------- 密码哈希 ----------
_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _pwd_ctx.verify(plain, hashed)
    except Exception:
        return False


# ---------- JWT ----------
_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def create_access_token(sub: str, expires_minutes: int | None = None, username: str | None = None) -> str:
    minutes = expires_minutes if expires_minutes is not None else settings.jwt_access_token_expire_minutes
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=minutes)).timestamp()),
        "type": "access",
    }
    if username:
        payload["username"] = username
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(sub: str, username: str | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=settings.jwt_refresh_token_expire_days)).timestamp()),
        "type": "refresh",
    }
    if username:
        payload["username"] = username
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None


# ---------- 用户加载 ----------
def load_user(db: Session, user_id: str) -> User | None:
    return db.get(User, user_id)


def authenticate(db: Session, username: str, password: str) -> User | None:
    user = db.query(User).filter(User.username == username).first()
    if not user or not user.enabled:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def build_user_info(db: Session, user: User) -> dict:
    """构造前端用户信息：角色/权限/菜单树。"""
    if user.is_super:
        role_codes = [r.code for r in user.roles] + ["*"]
        permissions = ["*"]
        menu_rows = db.query(Menu).order_by(Menu.sort).all()
    else:
        role_codes = [r.code for r in user.roles if r.enabled]
        perm_codes: set[str] = set()
        menu_ids: set[str] = set()
        for r in user.roles:
            if not r.enabled:
                continue
            for p in r.permissions:
                perm_codes.add(p.code)
            for m in r.menus:
                menu_ids.add(m.id)
        permissions = sorted(perm_codes)
        if menu_ids:
            menu_rows = (
                db.query(Menu)
                .filter(Menu.id.in_(menu_ids))
                .order_by(Menu.sort)
                .all()
            )
        else:
            menu_rows = []

    dept_name = user.dept.name if user.dept else None
    return {
        "id": user.id,
        "username": user.username,
        "nickname": user.nickname,
        "email": user.email,
        "phone": user.phone,
        "avatar": user.avatar,
        "is_super": user.is_super,
        "dept_id": user.dept_id,
        "dept_name": dept_name,
        "roles": role_codes,
        "permissions": permissions,
        "menus": [m_to_dict(m) for m in menu_rows],
    }


def m_to_dict(m: Menu) -> dict:
    return {
        "id": m.id,
        "parent_id": m.parent_id,
        "name": m.name,
        "path": m.path,
        "component": m.component,
        "icon": m.icon,
        "type": m.type,
        "permission_code": m.permission_code,
        "sort": m.sort,
        "visible": m.visible,
        "keep_alive": m.keep_alive,
    }


def build_menu_tree(menus: list[Menu]) -> list[dict]:
    """将扁平菜单列表构造为树。"""
    by_id = {m.id: {**m_to_dict(m), "children": []} for m in menus}
    roots: list[dict] = []
    for m in menus:
        node = by_id[m.id]
        if m.parent_id and m.parent_id in by_id:
            by_id[m.parent_id]["children"].append(node)
        else:
            roots.append(node)
    return roots


# ---------- FastAPI 依赖 ----------
def get_current_user(
    token: str | None = Depends(_oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="未认证或认证已过期",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise cred_exc
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise cred_exc
    user_id = payload.get("sub")
    if not user_id:
        raise cred_exc
    user = load_user(db, user_id)
    if not user or not user.enabled:
        raise cred_exc
    return user


def get_current_active_user(
    user: User = Depends(get_current_user),
) -> User:
    return user


def require_permissions(*codes: str):
    """权限校验依赖：超管或拥有任一权限码即可通过。"""

    def _dep(user: User = Depends(get_current_user)) -> User:
        if user.is_super:
            return user
        owned = {p.code for r in user.roles if r.enabled for p in r.permissions}
        if not codes or any(c in owned for c in codes):
            return user
        raise HTTPException(status_code=403, detail="权限不足")

    return _dep


def require_roles(*codes: str):
    """角色校验依赖：超管或拥有任一角色即可。"""

    def _dep(user: User = Depends(get_current_user)) -> User:
        if user.is_super:
            return user
        owned = {r.code for r in user.roles if r.enabled}
        if not codes or any(c in owned for c in codes):
            return user
        raise HTTPException(status_code=403, detail="角色权限不足")

    return _dep
