"""角色 API：CRUD + 角色-权限/菜单分配。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.rbac import Permission, Role, RoleMenu, RolePermission, Menu
from ..schemas.common import ApiResponse
from ..schemas.rbac import RoleCreate, RoleOut, RoleUpdate
from ..services.auth import require_permissions

router = APIRouter(prefix="/api/v1/roles", tags=["角色"])


def _to_out(r: Role) -> RoleOut:
    return RoleOut(
        id=r.id,
        code=r.code,
        name=r.name,
        description=r.description,
        data_scope=r.data_scope,
        sort=r.sort,
        enabled=r.enabled,
        permission_ids=[p.id for p in r.permissions],
        menu_ids=[m.id for m in r.menus],
    )


@router.get("", response_model=ApiResponse[list[RoleOut]])
def list_roles(
    db: Session = Depends(get_db),
    _=Depends(require_permissions("system:role:list")),
):
    items = db.query(Role).order_by(Role.sort).all()
    return ApiResponse(data=[_to_out(r) for r in items])


@router.post("", response_model=ApiResponse[RoleOut])
def create_role(
    payload: RoleCreate,
    db: Session = Depends(get_db),
    _=Depends(require_permissions("system:role:create")),
):
    if db.query(Role).filter(Role.code == payload.code).first():
        raise HTTPException(400, "角色编码已存在")
    role = Role(
        code=payload.code,
        name=payload.name,
        description=payload.description,
        data_scope=payload.data_scope,
        sort=payload.sort,
        enabled=payload.enabled,
    )
    if payload.permission_ids:
        perms = db.query(Permission).filter(Permission.id.in_(payload.permission_ids)).all()
        role.permissions = perms
    if payload.menu_ids:
        menus = db.query(Menu).filter(Menu.id.in_(payload.menu_ids)).all()
        role.menus = menus
    db.add(role)
    db.commit()
    db.refresh(role)
    return ApiResponse(data=_to_out(role))


@router.put("/{role_id}", response_model=ApiResponse[RoleOut])
def update_role(
    role_id: str,
    payload: RoleUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_permissions("system:role:update")),
):
    role = db.get(Role, role_id)
    if not role:
        raise HTTPException(404, "角色不存在")
    data = payload.model_dump(exclude_unset=True)
    perm_ids = data.pop("permission_ids", None)
    menu_ids = data.pop("menu_ids", None)
    for k, v in data.items():
        setattr(role, k, v)
    if perm_ids is not None:
        role.permissions = db.query(Permission).filter(Permission.id.in_(perm_ids)).all()
    if menu_ids is not None:
        role.menus = db.query(Menu).filter(Menu.id.in_(menu_ids)).all()
    db.commit()
    db.refresh(role)
    return ApiResponse(data=_to_out(role))


@router.delete("/{role_id}", response_model=ApiResponse[dict])
def delete_role(
    role_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_permissions("system:role:delete")),
):
    role = db.get(Role, role_id)
    if not role:
        raise HTTPException(404, "角色不存在")
    db.delete(role)
    db.commit()
    return ApiResponse(data={"ok": True})
