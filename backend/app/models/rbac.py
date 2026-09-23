"""RBAC 权限模型：用户/角色/权限/菜单/部门 + 关联表。"""
from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, GUID, TimestampMixin


# ---------- 部门 ----------
class Dept(Base, TimestampMixin):
    """部门（支持树形结构）。"""

    __tablename__ = "rbac_dept"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=GUID.default)
    parent_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("rbac_dept.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    code: Mapped[str | None] = mapped_column(String(64), unique=True)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    parent: Mapped["Dept | None"] = relationship(
        "Dept", remote_side="Dept.id", backref="children"
    )
    users: Mapped[list["User"]] = relationship("User", back_populates="dept")


# ---------- 用户 ----------
class User(Base, TimestampMixin):
    """系统用户。"""

    __tablename__ = "rbac_user"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=GUID.default)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    nickname: Mapped[str | None] = mapped_column(String(128))
    email: Mapped[str | None] = mapped_column(String(128))
    phone: Mapped[str | None] = mapped_column(String(32))
    hashed_password: Mapped[str] = mapped_column(String(256), nullable=False)
    avatar: Mapped[str | None] = mapped_column(String(256))
    dept_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("rbac_dept.id", ondelete="SET NULL"), nullable=True
    )
    is_super: Mapped[bool] = mapped_column(Boolean, default=False, comment="超级管理员")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[str | None] = mapped_column(String(64))

    dept: Mapped["Dept | None"] = relationship("Dept", back_populates="users")
    roles: Mapped[list["Role"]] = relationship(
        "Role", secondary="rbac_user_role", back_populates="users"
    )


# ---------- 角色 ----------
class Role(Base, TimestampMixin):
    """角色。"""

    __tablename__ = "rbac_role"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=GUID.default)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    data_scope: Mapped[str] = mapped_column(
        String(16), default="self", comment="all | dept | self"
    )
    sort: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    users: Mapped[list["User"]] = relationship(
        "User", secondary="rbac_user_role", back_populates="roles"
    )
    permissions: Mapped[list["Permission"]] = relationship(
        "Permission", secondary="rbac_role_permission", back_populates="roles"
    )
    menus: Mapped[list["Menu"]] = relationship(
        "Menu", secondary="rbac_role_menu", back_populates="roles"
    )


# ---------- 权限 ----------
class Permission(Base, TimestampMixin):
    """权限点（按钮/接口级）。"""

    __tablename__ = "rbac_permission"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=GUID.default)
    code: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    module: Mapped[str | None] = mapped_column(String(64), comment="所属模块")
    description: Mapped[str | None] = mapped_column(Text)

    roles: Mapped[list["Role"]] = relationship(
        "Role", secondary="rbac_role_permission", back_populates="permissions"
    )


# ---------- 菜单 ----------
class Menu(Base, TimestampMixin):
    """菜单/路由（树形）。"""

    __tablename__ = "rbac_menu"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=GUID.default)
    parent_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("rbac_menu.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    path: Mapped[str | None] = mapped_column(String(256))
    component: Mapped[str | None] = mapped_column(String(256))
    icon: Mapped[str | None] = mapped_column(String(64))
    type: Mapped[str] = mapped_column(
        String(16), default="menu", comment="catalog | menu | button"
    )
    permission_code: Mapped[str | None] = mapped_column(String(128))
    sort: Mapped[int] = mapped_column(Integer, default=0)
    visible: Mapped[bool] = mapped_column(Boolean, default=True)
    keep_alive: Mapped[bool] = mapped_column(Boolean, default=False)

    parent: Mapped["Menu | None"] = relationship(
        "Menu", remote_side="Menu.id", backref="children"
    )
    roles: Mapped[list["Role"]] = relationship(
        "Role", secondary="rbac_role_menu", back_populates="menus"
    )


# ---------- 关联表 ----------
class UserRole(Base):
    """用户-角色关联。"""

    __tablename__ = "rbac_user_role"
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uk_user_role"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=GUID.default)
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("rbac_user.id", ondelete="CASCADE"), nullable=False
    )
    role_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("rbac_role.id", ondelete="CASCADE"), nullable=False
    )


class RolePermission(Base):
    """角色-权限关联。"""

    __tablename__ = "rbac_role_permission"
    __table_args__ = (UniqueConstraint("role_id", "permission_id", name="uk_role_perm"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=GUID.default)
    role_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("rbac_role.id", ondelete="CASCADE"), nullable=False
    )
    permission_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("rbac_permission.id", ondelete="CASCADE"), nullable=False
    )


class RoleMenu(Base):
    """角色-菜单关联。"""

    __tablename__ = "rbac_role_menu"
    __table_args__ = (UniqueConstraint("role_id", "menu_id", name="uk_role_menu"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=GUID.default)
    role_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("rbac_role.id", ondelete="CASCADE"), nullable=False
    )
    menu_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("rbac_menu.id", ondelete="CASCADE"), nullable=False
    )


# ---------- 字典（数据源/数据项） ----------
class Dict(Base, TimestampMixin):
    """数据源/字典表（如：车辆类型、地形类型、任务状态）。"""

    __tablename__ = "sys_dict"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=GUID.default)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, comment="字典编码")
    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="字典名称")
    description: Mapped[str | None] = mapped_column(String(256))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    items: Mapped[list["DictItem"]] = relationship(
        "DictItem", back_populates="dict", cascade="all, delete-orphan"
    )


class DictItem(Base, TimestampMixin):
    """数据项：字典下的具体条目。"""

    __tablename__ = "sys_dict_item"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=GUID.default)
    dict_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("sys_dict.id", ondelete="CASCADE"), nullable=False
    )
    label: Mapped[str] = mapped_column(String(128), nullable=False, comment="显示文本")
    value: Mapped[str] = mapped_column(String(128), nullable=False, comment="实际值")
    sort: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    remark: Mapped[str | None] = mapped_column(String(256))

    dict: Mapped["Dict"] = relationship("Dict", back_populates="items")


# ---------- 系统参数 ----------
class SysParam(Base, TimestampMixin):
    """系统参数表（如：求解器时限、最大重规划次数）。"""

    __tablename__ = "sys_param"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=GUID.default)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, comment="参数编码")
    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="参数名称")
    value: Mapped[str] = mapped_column(String(512), nullable=False, comment="参数值")
    type: Mapped[str] = mapped_column(
        String(16), default="string", comment="string | number | bool"
    )
    remark: Mapped[str | None] = mapped_column(String(256))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


# ---------- 系统日志 ----------
class SysLog(Base, TimestampMixin):
    """系统操作日志表。"""

    __tablename__ = "sys_log"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=GUID.default)
    user_id: Mapped[str | None] = mapped_column(String(64))
    username: Mapped[str | None] = mapped_column(String(64))
    module: Mapped[str | None] = mapped_column(String(64), comment="业务模块")
    action: Mapped[str | None] = mapped_column(String(128), comment="操作描述")
    method: Mapped[str | None] = mapped_column(String(16), comment="HTTP 方法")
    url: Mapped[str | None] = mapped_column(String(512))
    params: Mapped[str | None] = mapped_column(Text, comment="请求参数/体")
    ip: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[int] = mapped_column(Integer, default=200, comment="HTTP 状态码")
    error_msg: Mapped[str | None] = mapped_column(Text)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, comment="耗时(ms)")
