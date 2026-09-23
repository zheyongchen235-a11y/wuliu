"""权限 API。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.rbac import Permission
from ..schemas.common import ApiResponse, Page
from ..schemas.rbac import PermissionCreate, PermissionOut, PermissionUpdate
from ..services.auth import require_permissions

router = APIRouter(prefix="/api/v1/permissions", tags=["权限"])


@router.get("", response_model=ApiResponse[list[PermissionOut]])
def list_permissions(
    module: str | None = Query(None),
    db: Session = Depends(get_db),
    _=Depends(require_permissions("system:permission:list")),
):
    q = db.query(Permission)
    if module:
        q = q.filter(Permission.module == module)
    items = q.order_by(Permission.module, Permission.code).all()
    return ApiResponse(data=[PermissionOut.model_validate(p) for p in items])


@router.post("", response_model=ApiResponse[PermissionOut])
def create_permission(
    payload: PermissionCreate,
    db: Session = Depends(get_db),
    _=Depends(require_permissions("system:permission:create")),
):
    if db.query(Permission).filter(Permission.code == payload.code).first():
        raise HTTPException(400, "权限编码已存在")
    perm = Permission(**payload.model_dump())
    db.add(perm)
    db.commit()
    db.refresh(perm)
    return ApiResponse(data=PermissionOut.model_validate(perm))


@router.put("/{perm_id}", response_model=ApiResponse[PermissionOut])
def update_permission(
    perm_id: str,
    payload: PermissionUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_permissions("system:permission:update")),
):
    perm = db.get(Permission, perm_id)
    if not perm:
        raise HTTPException(404, "权限不存在")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(perm, k, v)
    db.commit()
    db.refresh(perm)
    return ApiResponse(data=PermissionOut.model_validate(perm))


@router.delete("/{perm_id}", response_model=ApiResponse[dict])
def delete_permission(
    perm_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_permissions("system:permission:delete")),
):
    perm = db.get(Permission, perm_id)
    if not perm:
        raise HTTPException(404, "权限不存在")
    db.delete(perm)
    db.commit()
    return ApiResponse(data={"ok": True})
