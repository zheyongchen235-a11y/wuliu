"""系统参数管理 API：CRUD。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.rbac import SysParam
from ..schemas.common import ApiResponse, Page
from ..schemas.rbac import SysParamCreate, SysParamOut, SysParamUpdate
from ..services.auth import require_permissions

router = APIRouter(prefix="/api/v1/params", tags=["系统参数"])


def _to_out(p: SysParam) -> SysParamOut:
    return SysParamOut(
        id=p.id,
        code=p.code,
        name=p.name,
        value=p.value,
        type=p.type,
        remark=p.remark,
        enabled=p.enabled,
    )


@router.get("", response_model=ApiResponse[Page[SysParamOut]])
def list_params(
    keyword: str | None = Query(None),
    enabled: bool | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _=Depends(require_permissions("system:param:list")),
):
    q = db.query(SysParam)
    if keyword:
        kw = f"%{keyword}%"
        q = q.filter(or_(SysParam.code.like(kw), SysParam.name.like(kw)))
    if enabled is not None:
        q = q.filter(SysParam.enabled == enabled)
    total = q.count()
    rows = (
        q.order_by(SysParam.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return ApiResponse(
        data=Page(
            items=[_to_out(p) for p in rows],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.post("", response_model=ApiResponse[SysParamOut])
def create_param(
    payload: SysParamCreate,
    db: Session = Depends(get_db),
    _=Depends(require_permissions("system:param:create")),
):
    if db.query(SysParam).filter(SysParam.code == payload.code).first():
        raise HTTPException(400, "参数编码已存在")
    p = SysParam(
        code=payload.code,
        name=payload.name,
        value=payload.value,
        type=payload.type,
        remark=payload.remark,
        enabled=payload.enabled,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return ApiResponse(data=_to_out(p))


@router.put("/{param_id}", response_model=ApiResponse[SysParamOut])
def update_param(
    param_id: str,
    payload: SysParamUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_permissions("system:param:update")),
):
    p = db.get(SysParam, param_id)
    if not p:
        raise HTTPException(404, "参数不存在")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return ApiResponse(data=_to_out(p))


@router.delete("/{param_id}", response_model=ApiResponse[dict])
def delete_param(
    param_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_permissions("system:param:delete")),
):
    p = db.get(SysParam, param_id)
    if not p:
        raise HTTPException(404, "参数不存在")
    db.delete(p)
    db.commit()
    return ApiResponse(data={"ok": True})
