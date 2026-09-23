"""Pydantic schemas."""
from .basic import (
    StoreCreate,
    StoreUpdate,
    StoreOut,
    RouteCreate,
    RouteOut,
    VehicleCreate,
    VehicleOut,
    DriverOut,
    StoreRouteMappingOut,
)
from .rules import (
    TerrainRuleOut,
    TripRuleOut,
    LoadRuleOut,
    ConstraintConfigCreate,
    ConstraintConfigOut,
)
from .scheduling import (
    CreateTaskRequest,
    TaskOut,
    PlanOut,
    PlanDetailOut,
    PlanScoreOut,
    ConfirmRequest,
    ReplanRequest,
    ExceptionEventCreate,
    ExceptionEventOut,
    ExecutionFeedback,
    TaskProgressMessage,
)
from .report import ReportOut, AttendanceReport, LoadRateReport, TripAchievementReport
from .rbac import (
    LoginRequest,
    TokenResponse,
    UserInfo,
    DeptCreate,
    DeptUpdate,
    DeptOut,
    DeptTree,
    UserCreate,
    UserUpdate,
    PasswordChange,
    UserResetPassword,
    UserOut,
    RoleCreate,
    RoleUpdate,
    RoleOut,
    PermissionCreate,
    PermissionUpdate,
    PermissionOut,
    MenuCreate,
    MenuUpdate,
    MenuOut,
    MenuTree,
)

