"""部门 API：CRUD + 树。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.rbac import Dept
from ..schemas.common import ApiResponse
from ..schemas.rbac import DeptCreate, DeptOut, DeptTree, DeptUpdate
from ..services.auth import require_permissions

router = APIRouter(prefix="/api/v1/depts", tags=["部门"])


@router.get("", response_model=ApiResponse[list[DeptOut]])
def list_depts(
    db: Session = Depends(get_db),
    _=Depends(require_permissions("system:dept:list")),
):
    items = db.query(Dept).order_by(Dept.sort).all()
    return ApiResponse(data=[DeptOut.model_validate(d) for d in items])


@router.get("/tree", response_model=ApiResponse[list[DeptTree]])
def dept_tree(
    db: Session = Depends(get_db),
    _=Depends(require_permissions("system:dept:list")),
):
    items = db.query(Dept).order_by(Dept.sort).all()
    by_id = {d.id: {**DeptOut.model_validate(d).model_dump(), "children": []} for d in items}
    roots: list[dict] = []
    for d in items:
        node = by_id[d.id]
        if d.parent_id and d.parent_id in by_id:
            by_id[d.parent_id]["children"].append(node)
        else:
            roots.append(node)
    return ApiResponse(data=[DeptTree.model_validate(r) for r in roots])


@router.post("", response_model=ApiResponse[DeptOut])
def create_dept(
    payload: DeptCreate,
    db: Session = Depends(get_db),
    _=Depends(require_permissions("system:dept:create")),
):
    dept = Dept(**payload.model_dump())
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return ApiResponse(data=DeptOut.model_validate(dept))


@router.put("/{dept_id}", response_model=ApiResponse[DeptOut])
def update_dept(
    dept_id: str,
    payload: DeptUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_permissions("system:dept:update")),
):
    dept = db.get(Dept, dept_id)
    if not dept:
        raise HTTPException(404, "部门不存在")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(dept, k, v)
    db.commit()
    db.refresh(dept)
    return ApiResponse(data=DeptOut.model_validate(dept))


@router.delete("/{dept_id}", response_model=ApiResponse[dict])
def delete_dept(
    dept_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_permissions("system:dept:delete")),
):
    dept = db.get(Dept, dept_id)
    if not dept:
        raise HTTPException(404, "部门不存在")
    db.delete(dept)
    db.commit()
    return ApiResponse(data={"ok": True})
