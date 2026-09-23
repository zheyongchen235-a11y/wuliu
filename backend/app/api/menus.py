"""菜单 API：CRUD + 树。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.rbac import Menu
from ..schemas.common import ApiResponse
from ..schemas.rbac import MenuCreate, MenuOut, MenuTree, MenuUpdate
from ..services.auth import require_permissions

router = APIRouter(prefix="/api/v1/menus", tags=["菜单"])


def _to_out(m: Menu) -> dict:
    return MenuOut.model_validate(m).model_dump()


@router.get("", response_model=ApiResponse[list[MenuOut]])
def list_menus(
    db: Session = Depends(get_db),
    _=Depends(require_permissions("system:menu:list")),
):
    items = db.query(Menu).order_by(Menu.sort).all()
    return ApiResponse(data=[MenuOut.model_validate(m) for m in items])


@router.get("/tree", response_model=ApiResponse[list[MenuTree]])
def menu_tree(
    db: Session = Depends(get_db),
    _=Depends(require_permissions("system:menu:list")),
):
    items = db.query(Menu).order_by(Menu.sort).all()
    by_id = {m.id: {**_to_out(m), "children": []} for m in items}
    roots: list[dict] = []
    for m in items:
        node = by_id[m.id]
        if m.parent_id and m.parent_id in by_id:
            by_id[m.parent_id]["children"].append(node)
        else:
            roots.append(node)
    return ApiResponse(data=[MenuTree.model_validate(r) for r in roots])


@router.post("", response_model=ApiResponse[MenuOut])
def create_menu(
    payload: MenuCreate,
    db: Session = Depends(get_db),
    _=Depends(require_permissions("system:menu:create")),
):
    menu = Menu(**payload.model_dump())
    db.add(menu)
    db.commit()
    db.refresh(menu)
    return ApiResponse(data=MenuOut.model_validate(menu))


@router.put("/{menu_id}", response_model=ApiResponse[MenuOut])
def update_menu(
    menu_id: str,
    payload: MenuUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_permissions("system:menu:update")),
):
    menu = db.get(Menu, menu_id)
    if not menu:
        raise HTTPException(404, "菜单不存在")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(menu, k, v)
    db.commit()
    db.refresh(menu)
    return ApiResponse(data=MenuOut.model_validate(menu))


@router.delete("/{menu_id}", response_model=ApiResponse[dict])
def delete_menu(
    menu_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_permissions("system:menu:delete")),
):
    menu = db.get(Menu, menu_id)
    if not menu:
        raise HTTPException(404, "菜单不存在")
    db.delete(menu)
    db.commit()
    return ApiResponse(data={"ok": True})
