"""FastAPI 应用入口.

对应技术方案 5.x 节：REST API + WebSocket + CORS + 启动初始化。
"""
from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from .api import basic as basic_api
from .api import reports as reports_api
from .api import rules as rules_api
from .api import scheduling as scheduling_api
from .api import ws as ws_api
from .api import auth as auth_api
from .api import depts as depts_api
from .api import dicts as dicts_api
from .api import logs as logs_api
from .api import menus as menus_api
from .api import params as params_api
from .api import permissions as permissions_api
from .api import roles as roles_api
from .api import users as users_api
from .config import settings
from .database import SessionLocal, init_db
from .services.auth import decode_token

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ---------- 全局 JWT 认证中间件 ----------
PUBLIC_PREFIXES = ("/docs", "/openapi", "/redoc")
PUBLIC_PATHS = {
    "/",
    "/health",
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
}

# 路由前缀 → 业务模块映射，用于日志归类
_MODULE_MAP = [
    ("/api/v1/auth", "auth"),
    ("/api/v1/users", "user"),
    ("/api/v1/roles", "role"),
    ("/api/v1/permissions", "permission"),
    ("/api/v1/menus", "menu"),
    ("/api/v1/depts", "dept"),
    ("/api/v1/dicts", "dict"),
    ("/api/v1/params", "param"),
    ("/api/v1/logs", "log"),
    ("/api/v1/stores", "store"),
    ("/api/v1/vehicles", "vehicle"),
    ("/api/v1/routes", "route"),
    ("/api/v1/drivers", "driver"),
    ("/api/v1/rules", "rule"),
    ("/api/v1/scheduling", "scheduling"),
    ("/api/v1/reports", "report"),
]


def _resolve_module(path: str) -> str | None:
    for prefix, name in _MODULE_MAP:
        if path.startswith(prefix):
            return name
    return None


def _resolve_action(method: str, path: str) -> str:
    """根据 HTTP 方法推断操作描述。"""
    m = method.upper()
    if m == "GET":
        return "查询"
    if m == "POST":
        return "新增"
    if m == "PUT":
        return "修改"
    if m == "DELETE":
        return "删除"
    return m


class JwtAuthMiddleware(BaseHTTPMiddleware):
    """对 /api/ 开头的请求校验 Bearer JWT（公共路径放行）。"""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in PUBLIC_PATHS or any(path.startswith(p) for p in PUBLIC_PREFIXES):
            return await call_next(request)
        if not path.startswith("/api/"):
            # /ws/ 与静态资源不强制鉴权
            return await call_next(request)
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return JSONResponse(
                {"code": 401, "message": "未提供认证令牌"},
                status_code=401,
            )
        token = auth[7:].strip()
        payload = decode_token(token)
        if not payload or payload.get("type") != "access":
            return JSONResponse(
                {"code": 401, "message": "认证令牌无效或已过期"},
                status_code=401,
            )
        request.state.user_id = payload.get("sub")
        request.state.username = payload.get("username")
        return await call_next(request)


class AuditLogMiddleware(BaseHTTPMiddleware):
    """记录 /api/ 写操作到 sys_log 表。

    GET 查询量大默认不入库；/api/v1/logs 自身不记录以免刷屏。
    仅记录 query string，不读取请求体（避免破坏下游 body 读取）。
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method.upper()
        if (
            not path.startswith("/api/")
            or path in PUBLIC_PATHS
            or method == "GET"
            or path.startswith("/api/v1/logs")
        ):
            return await call_next(request)

        start = time.perf_counter()
        query = request.url.query

        try:
            response = await call_next(request)
            status_code = response.status_code
            error_msg = None
        except Exception as e:  # noqa: BLE001
            response = JSONResponse(
                {"code": 500, "message": f"服务器内部错误: {e}"},
                status_code=500,
            )
            status_code = 500
            error_msg = str(e)[:1000]

        latency_ms = int((time.perf_counter() - start) * 1000)

        # 同步短事务入库（数据量小）
        try:
            user_id = getattr(request.state, "user_id", None)
            username = getattr(request.state, "username", None)
            client_ip = request.client.host if request.client else None
            params_text = query if query else None
            from .models.rbac import SysLog

            with SessionLocal() as db:
                db.add(
                    SysLog(
                        user_id=user_id,
                        username=username,
                        module=_resolve_module(path),
                        action=_resolve_action(method, path),
                        method=method,
                        url=path,
                        params=params_text,
                        ip=client_ip,
                        status=status_code,
                        error_msg=error_msg,
                        latency_ms=latency_ms,
                    )
                )
                db.commit()
        except Exception as e:  # noqa: BLE001
            logger.warning(f"写入审计日志失败：{e}")

        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("初始化数据库...")
    init_db()
    logger.info("数据库就绪")
    # 自动 seed 超管与默认 RBAC
    try:
        from .seed import ensure_rbac_seed

        ensure_rbac_seed()
        logger.info("RBAC 种子数据已就绪")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"RBAC 种子初始化失败：{e}")
    yield
    logger.info("应用关闭")


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="车辆智能调度 Agent 后端 - FastAPI + LangGraph + OR-Tools",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# 中间件执行顺序：后注册的越靠外。JwtAuth 最后注册 → 最外层 → 先执行，
# 它设置 request.state.user_id/username 后，AuditLog 才读取，顺序正确。
app.add_middleware(AuditLogMiddleware)
app.add_middleware(JwtAuthMiddleware)

# 业务路由
app.include_router(basic_api.router)
app.include_router(rules_api.router)
app.include_router(scheduling_api.router)
app.include_router(reports_api.router)
app.include_router(ws_api.router)

# RBAC 路由
app.include_router(auth_api.router)
app.include_router(users_api.router)
app.include_router(roles_api.router)
app.include_router(permissions_api.router)
app.include_router(menus_api.router)
app.include_router(depts_api.router)
app.include_router(dicts_api.router)
app.include_router(params_api.router)
app.include_router(logs_api.router)


@app.get("/", tags=["系统"])
async def root():
    return {
        "app": settings.app_name,
        "version": settings.version,
        "docs": "/docs",
        "endpoints": [
            "/api/v1/auth/login",
            "/api/v1/auth/me",
            "/api/v1/users",
            "/api/v1/roles",
            "/api/v1/permissions",
            "/api/v1/menus",
            "/api/v1/depts",
            "/api/v1/dicts",
            "/api/v1/params",
            "/api/v1/logs",
            "/api/v1/stores",
            "/api/v1/vehicles",
            "/api/v1/routes",
            "/api/v1/rules/constraints",
            "/api/v1/scheduling/tasks",
            "/api/v1/reports/attendance",
            "/ws/scheduling/{task_id}",
        ],
    }


@app.get("/health", tags=["系统"])
async def health():
    return {"status": "ok"}
