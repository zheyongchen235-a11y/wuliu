"""应用配置."""
from __future__ import annotations

import os
from pathlib import Path
from pydantic import BaseModel, Field


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseModel):
    """全局配置项。可通过环境变量覆盖。"""

    app_name: str = "车辆智能调度 Agent"
    version: str = "0.2.0"
    debug: bool = Field(default=False)

    # 数据库（默认使用 MySQL；演示可改回 sqlite）
    database_url: str = Field(
        default="mysql+pymysql://sched:sched123@localhost:3306/scheduling?charset=utf8mb4",
        description="SQLAlchemy 数据库连接字符串",
    )

    # Redis（可选，未配置时降级为内存锁/缓存）
    redis_url: str | None = None

    # JWT / RBAC
    jwt_secret_key: str = Field(default="change-me-in-production-please")
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 12  # 12 小时
    jwt_refresh_token_expire_days: int = 7

    # RBAC 超级管理员（首次 seed 自动创建）
    super_admin_username: str = "admin"
    super_admin_password: str = "admin123"

    # LLM 配置
    llm_provider: str = Field(default="mock", description="mock | openai | qwen | deepseek")
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    llm_model: str = "gpt-4o-mini"

    # TMS 集成
    tms_base_url: str = Field(default="http://localhost:8000/mock/tms")
    tms_timeout: float = 5.0

    # 求解器
    solver_time_limit_sec: float = 5.0
    solver_max_plans: int = 4

    # 调度约束默认值
    vehicle_42_min_load: int = 630
    vehicle_42_max_load: int = 800
    vehicle_42_count: int = 28
    vehicle_42_trips: int = 2
    vehicle_big_min_load: int = 300
    vehicle_big_max_load: int = 420
    vehicle_big_count: int = 3
    vehicle_big_trips: int = 2
    vehicle_small_min_load: int = 1
    vehicle_small_max_load: int = 300
    vehicle_small_count: int = 9
    vehicle_small_trips: int = 4

    max_replan_count: int = 3

    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:8080", "http://localhost:5173", "http://127.0.0.1:8080"]
    )

    class Config:
        env_prefix = "SCHED_"
        env_file = ".env"
        extra = "ignore"


def _load_env_file() -> None:
    """简单加载 backend/.env（KEY=VALUE），不覆盖已存在的环境变量。"""
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v
    except Exception:
        pass


def get_settings() -> Settings:
    """构造 Settings 实例（每次调用读取最新环境变量）。"""
    _load_env_file()
    defaults = Settings()

    provider = os.getenv("SCHED_LLM_PROVIDER", "mock")
    # deepseek provider：回退读取 DEEPSEEK_API_KEY / DEEPSEEK_API_BASE 系统环境变量
    if provider == "deepseek":
        llm_api_key = os.getenv("SCHED_LLM_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
        llm_base_url = (
            os.getenv("SCHED_LLM_BASE_URL")
            or os.getenv("DEEPSEEK_API_BASE")
            or "https://api.deepseek.com"
        )
        llm_model = os.getenv("SCHED_LLM_MODEL", "deepseek-chat")
    else:
        llm_api_key = os.getenv("SCHED_LLM_API_KEY") or None
        llm_base_url = os.getenv("SCHED_LLM_BASE_URL") or None
        llm_model = os.getenv("SCHED_LLM_MODEL", "gpt-4o-mini")

    data = {
        "app_name": os.getenv("SCHED_APP_NAME", defaults.app_name),
        "debug": os.getenv("SCHED_DEBUG", "false").lower() in ("1", "true", "yes"),
        "database_url": os.getenv(
            "SCHED_DATABASE_URL",
            "mysql+pymysql://sched:sched123@localhost:3306/scheduling?charset=utf8mb4",
        ),
        "redis_url": os.getenv("SCHED_REDIS_URL") or None,
        "jwt_secret_key": os.getenv("SCHED_JWT_SECRET_KEY", defaults.jwt_secret_key),
        "jwt_access_token_expire_minutes": int(
            os.getenv("SCHED_JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "720")
        ),
        "super_admin_username": os.getenv("SCHED_SUPER_ADMIN_USERNAME", "admin"),
        "super_admin_password": os.getenv("SCHED_SUPER_ADMIN_PASSWORD", "admin123"),
        "llm_provider": provider,
        "llm_api_key": llm_api_key,
        "llm_base_url": llm_base_url,
        "llm_model": llm_model,
        "tms_base_url": os.getenv("SCHED_TMS_BASE_URL", "http://localhost:8000/mock/tms"),
        "solver_time_limit_sec": float(os.getenv("SCHED_SOLVER_TIME_LIMIT_SEC", "5")),
    }
    return Settings(**data)


settings = get_settings()
