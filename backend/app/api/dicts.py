"""字典管理 API：数据源 CRUD + 数据项 CRUD。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.rbac import Dict, DictItem
from ..schemas.common import ApiResponse, Page
from ..schemas.rbac import (
    DictCreate,
    DictItemCreate,
    DictItemOut,
    DictItemUpdate,
    DictOut,
    DictUpdate,
)
from ..services.auth import require_permissions

router = APIRouter(prefix="/api/v1/dicts", tags=["字典管理"])


def _dict_out(d: Dict) -> DictOut:
    return DictOut(
        id=d.id,
        code=d.code,
        name=d.name,
        description=d.description,
        enabled=d.enabled,
    )


def _item_out(it: DictItem) -> DictItemOut:
    return DictItemOut(
        id=it.id,
        dict_id=it.dict_id,
        label=it.label,
        value=it.value,
        sort=it.sort,
        enabled=it.enabled,
        remark=it.remark,
    )


# ---------- 字典（数据源） ----------
@router.get("", response_model=ApiResponse[list[DictOut]])
def list_dicts(
    keyword: str | None = Query(None),
    enabled: bool | None = Query(None),
    db: Session = Depends(get_db),
    _=Depends(require_permissions("system:dict:list")),
):
    q = db.query(Dict)
    if keyword:
        kw = f"%{keyword}%"
        q = q.filter(or_(Dict.code.like(kw), Dict.name.like(kw)))
    if enabled is not None:
        q = q.filter(Dict.enabled == enabled)
    rows = q.order_by(Dict.created_at.desc()).all()
    return ApiResponse(data=[_dict_out(d) for d in rows])


@router.post("", response_model=ApiResponse[DictOut])
def create_dict(
    payload: DictCreate,
    db: Session = Depends(get_db),
    _=Depends(require_permissions("system:dict:create")),
):
    if db.query(Dict).filter(Dict.code == payload.code).first():
        raise HTTPException(400, "字典编码已存在")
    d = Dict(
        code=payload.code,
        name=payload.name,
        description=payload.description,
        enabled=payload.enabled,
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return ApiResponse(data=_dict_out(d))


@router.put("/{dict_id}", response_model=ApiResponse[DictOut])
def update_dict(
    dict_id: str,
    payload: DictUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_permissions("system:dict:update")),
):
    d = db.get(Dict, dict_id)
    if not d:
        raise HTTPException(404, "字典不存在")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(d, k, v)
    db.commit()
    db.refresh(d)
    return ApiResponse(data=_dict_out(d))


@router.delete("/{dict_id}", response_model=ApiResponse[dict])
def delete_dict(
    dict_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_permissions("system:dict:delete")),
):
    d = db.get(Dict, dict_id)
    if not d:
        raise HTTPException(404, "字典不存在")
    db.delete(d)
    db.commit()
    return ApiResponse(data={"ok": True})


# ---------- 数据项 ----------
@router.get("/{dict_id}/items", response_model=ApiResponse[list[DictItemOut]])
def list_items(
    dict_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_permissions("system:dict:list")),
):
    if not db.get(Dict, dict_id):
        raise HTTPException(404, "字典不存在")
    rows = (
        db.query(DictItem)
        .filter(DictItem.dict_id == dict_id)
        .order_by(DictItem.sort, DictItem.created_at)
        .all()
    )
    return ApiResponse(data=[_item_out(it) for it in rows])


@router.post("/{dict_id}/items", response_model=ApiResponse[DictItemOut])
def create_item(
    dict_id: str,
    payload: DictItemCreate,
    db: Session = Depends(get_db),
    _=Depends(require_permissions("system:dict:create")),
):
    if not db.get(Dict, dict_id):
        raise HTTPException(404, "字典不存在")
    it = DictItem(
        dict_id=dict_id,
        label=payload.label,
        value=payload.value,
        sort=payload.sort,
        enabled=payload.enabled,
        remark=payload.remark,
    )
    db.add(it)
    db.commit()
    db.refresh(it)
    return ApiResponse(data=_item_out(it))


@router.put("/{dict_id}/items/{item_id}", response_model=ApiResponse[DictItemOut])
def update_item(
    dict_id: str,
    item_id: str,
    payload: DictItemUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_permissions("system:dict:update")),
):
    it = db.get(DictItem, item_id)
    if not it or it.dict_id != dict_id:
        raise HTTPException(404, "数据项不存在")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(it, k, v)
    db.commit()
    db.refresh(it)
    return ApiResponse(data=_item_out(it))


@router.delete("/{dict_id}/items/{item_id}", response_model=ApiResponse[dict])
def delete_item(
    dict_id: str,
    item_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_permissions("system:dict:delete")),
):
    it = db.get(DictItem, item_id)
    if not it or it.dict_id != dict_id:
        raise HTTPException(404, "数据项不存在")
    db.delete(it)
    db.commit()
    return ApiResponse(data={"ok": True})
