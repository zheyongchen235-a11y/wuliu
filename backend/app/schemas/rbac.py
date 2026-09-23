"""RBAC 相关 Pydantic schema。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from .common import ORMModel


# ---------- 认证 ----------
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int


class UserInfo(BaseModel):
    """登录用户信息（含角色/权限/菜单）。"""

    id: str
    username: str
    nickname: str | None = None
    email: str | None = None
    phone: str | None = None
    avatar: str | None = None
    is_super: bool = False
    dept_id: str | None = None
    dept_name: str | None = None
    roles: list[str] = Field(default_factory=list, description="角色 code 列表")
    permissions: list[str] = Field(default_factory=list, description="权限 code 列表")
    menus: list["MenuTree"] = Field(default_factory=list)


# ---------- 部门 ----------
class DeptBase(BaseModel):
    name: str
    parent_id: str | None = None
    code: str | None = None
    sort: int = 0
    enabled: bool = True


class DeptCreate(DeptBase):
    pass


class DeptUpdate(BaseModel):
    name: str | None = None
    parent_id: str | None = None
    code: str | None = None
    sort: int | None = None
    enabled: bool | None = None


class DeptOut(ORMModel):
    id: str
    name: str
    parent_id: str | None
    code: str | None
    sort: int
    enabled: bool


class DeptTree(ORMModel):
    id: str
    name: str
    parent_id: str | None
    code: str | None
    sort: int
    enabled: bool
    children: list["DeptTree"] = Field(default_factory=list)


# ---------- 用户 ----------
class UserCreate(BaseModel):
    username: str
    password: str
    nickname: str | None = None
    email: str | None = None
    phone: str | None = None
    dept_id: str | None = None
    role_ids: list[str] = Field(default_factory=list)
    is_super: bool = False
    enabled: bool = True


class UserUpdate(BaseModel):
    nickname: str | None = None
    email: str | None = None
    phone: str | None = None
    avatar: str | None = None
    dept_id: str | None = None
    role_ids: list[str] | None = None
    is_super: bool | None = None
    enabled: bool | None = None


class PasswordChange(BaseModel):
    old_password: str
    new_password: str


class UserResetPassword(BaseModel):
    new_password: str


class UserOut(ORMModel):
    id: str
    username: str
    nickname: str | None
    email: str | None
    phone: str | None
    avatar: str | None
    dept_id: str | None
    is_super: bool
    enabled: bool
    last_login_at: str | None
    role_ids: list[str] = Field(default_factory=list)
    role_codes: list[str] = Field(default_factory=list)
    dept_name: str | None = None


# ---------- 角色 ----------
class RoleBase(BaseModel):
    code: str
    name: str
    description: str | None = None
    data_scope: str = "self"
    sort: int = 0
    enabled: bool = True


class RoleCreate(RoleBase):
    permission_ids: list[str] = Field(default_factory=list)
    menu_ids: list[str] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    data_scope: str | None = None
    sort: int | None = None
    enabled: bool | None = None
    permission_ids: list[str] | None = None
    menu_ids: list[str] | None = None


class RoleOut(ORMModel):
    id: str
    code: str
    name: str
    description: str | None
    data_scope: str
    sort: int
    enabled: bool
    permission_ids: list[str] = Field(default_factory=list)
    menu_ids: list[str] = Field(default_factory=list)


# ---------- 权限 ----------
class PermissionCreate(BaseModel):
    code: str
    name: str
    module: str | None = None
    description: str | None = None


class PermissionUpdate(BaseModel):
    name: str | None = None
    module: str | None = None
    description: str | None = None


class PermissionOut(ORMModel):
    id: str
    code: str
    name: str
    module: str | None
    description: str | None


# ---------- 菜单 ----------
class MenuBase(BaseModel):
    name: str
    parent_id: str | None = None
    path: str | None = None
    component: str | None = None
    icon: str | None = None
    type: str = "menu"
    permission_code: str | None = None
    sort: int = 0
    visible: bool = True
    keep_alive: bool = False


class MenuCreate(MenuBase):
    pass


class MenuUpdate(BaseModel):
    name: str | None = None
    parent_id: str | None = None
    path: str | None = None
    component: str | None = None
    icon: str | None = None
    type: str | None = None
    permission_code: str | None = None
    sort: int | None = None
    visible: bool | None = None
    keep_alive: bool | None = None


class MenuOut(ORMModel):
    id: str
    parent_id: str | None
    name: str
    path: str | None
    component: str | None
    icon: str | None
    type: str
    permission_code: str | None
    sort: int
    visible: bool
    keep_alive: bool


class MenuTree(MenuOut):
    children: list["MenuTree"] = Field(default_factory=list)


# ---------- 字典（数据源/数据项） ----------
class DictCreate(BaseModel):
    code: str
    name: str
    description: str | None = None
    enabled: bool = True


class DictUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    enabled: bool | None = None


class DictItemCreate(BaseModel):
    label: str
    value: str
    sort: int = 0
    enabled: bool = True
    remark: str | None = None


class DictItemUpdate(BaseModel):
    label: str | None = None
    value: str | None = None
    sort: int | None = None
    enabled: bool | None = None
    remark: str | None = None


class DictItemOut(ORMModel):
    id: str
    dict_id: str
    label: str
    value: str
    sort: int
    enabled: bool
    remark: str | None


class DictOut(ORMModel):
    id: str
    code: str
    name: str
    description: str | None
    enabled: bool


# ---------- 系统参数 ----------
class SysParamCreate(BaseModel):
    code: str
    name: str
    value: str
    type: str = "string"
    remark: str | None = None
    enabled: bool = True


class SysParamUpdate(BaseModel):
    name: str | None = None
    value: str | None = None
    type: str | None = None
    remark: str | None = None
    enabled: bool | None = None


class SysParamOut(ORMModel):
    id: str
    code: str
    name: str
    value: str
    type: str
    remark: str | None
    enabled: bool


# ---------- 系统日志 ----------
class SysLogOut(ORMModel):
    id: str
    user_id: str | None
    username: str | None
    module: str | None
    action: str | None
    method: str | None
    url: str | None
    params: str | None
    ip: str | None
    status: int
    error_msg: str | None
    latency_ms: int
    created_at: datetime | None


# 解决前向引用
UserInfo.model_rebuild()
MenuTree.model_rebuild()
DeptTree.model_rebuild()
