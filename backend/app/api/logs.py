"""系统日志管理 API：列表（分页+筛选）/删除/清空。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.rbac import SysLog
from ..schemas.common import ApiResponse, Page
from ..schemas.rbac import SysLogOut
from ..services.auth import require_permissions

router = APIRouter(prefix="/api/v1/logs", tags=["系统日志"])


def _to_out(log: SysLog) -> SysLogOut:
    return SysLogOut(
        id=log.id,
        user_id=log.user_id,
        username=log.username,
        module=log.module,
        action=log.action,
        method=log.method,
        url=log.url,
        params=log.params,
        ip=log.ip,
        status=log.status,
        error_msg=log.error_msg,
        latency_ms=log.latency_ms,
        created_at=log.created_at,
    )


@router.get("", response_model=ApiResponse[Page[SysLogOut]])
def list_logs(
    keyword: str | None = Query(None),
    module: str | None = Query(None),
    username: str | None = Query(None),
    status: int | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _=Depends(require_permissions("system:log:list")),
):
    q = db.query(SysLog)
    if keyword:
        kw = f"%{keyword}%"
        q = q.filter(
            or_(
                SysLog.action.like(kw),
                SysLog.url.like(kw),
                SysLog.error_msg.like(kw),
            )
        )
    if module:
        q = q.filter(SysLog.module == module)
    if username:
        q = q.filter(SysLog.username == username)
    if status is not None:
        if status == 2:
            # 2 表示查询非 2xx
            q = q.filter((SysLog.status < 200) | (SysLog.status >= 300))
        else:
            q = q.filter(SysLog.status == status)
    total = q.count()
    rows = (
        q.order_by(SysLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return ApiResponse(
        data=Page(
            items=[_to_out(r) for r in rows],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.delete("/{log_id}", response_model=ApiResponse[dict])
def delete_log(
    log_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_permissions("system:log:delete")),
):
    log = db.get(SysLog, log_id)
    if not log:
        raise HTTPException(404, "日志不存在")
    db.delete(log)
    db.commit()
    return ApiResponse(data={"ok": True})


@router.delete("", response_model=ApiResponse[dict])
def clear_logs(
    db: Session = Depends(get_db),
    _=Depends(require_permissions("system:log:delete")),
):
    """清空全部日志。"""
    db.query(SysLog).delete(synchronize_session=False)
    db.commit()
    return ApiResponse(data={"ok": True})
