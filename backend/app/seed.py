"""种子数据：门店、线路、车辆、司机、规则、约束配置.

Usage:
    py -3.12 -m app.seed
"""
from __future__ import annotations

import random
from datetime import date

from .database import SessionLocal, init_db
from .models.basic import (
    Driver,
    Route,
    Store,
    StoreRouteMapping,
    Vehicle,
    VehicleTerrainCapability,
    Warehouse,
)
from .models.rules import (
    ConstraintConfig,
    LoadRule,
    TerrainRule,
    TripRule,
)
from .models.rbac import Dept, Dict, DictItem, Menu, Permission, Role, SysParam, User
from .services.auth import hash_password
from .config import settings


WAREHOUSES = [
    ("W01", "市中心仓", "城西物流园"),
    ("W02", "城北仓", "城北物流园"),
]

ROUTES = [
    ("R001", "城东线", "normal"),
    ("R002", "城南线", "normal"),
    ("R003", "城西线", "mid"),
    ("R004", "城北线", "normal"),
    ("R005", "山区线", "strict"),
    ("R006", "老城线", "mid"),
]

DRIVERS = [
    ("D001", "张三", "13800000001"),
    ("D002", "李四", "13800000002"),
    ("D003", "王五", "13800000003"),
    ("D004", "赵六", "13800000004"),
    ("D005", "钱七", "13800000005"),
]


def seed_all() -> None:
    init_db()
    rng = random.Random(42)
    with SessionLocal() as db:
        # 仓库
        for wid, name, addr in WAREHOUSES:
            if db.get(Warehouse, wid) is None:
                db.add(Warehouse(id=wid, name=name, address=addr))
        db.commit()

        # 线路
        for rid, name, terrain in ROUTES:
            if db.get(Route, rid) is None:
                db.add(Route(id=rid, name=name, terrain_type=terrain))
        db.commit()

        # 司机
        for did, name, phone in DRIVERS:
            if db.get(Driver, did) is None:
                db.add(Driver(id=did, name=name, phone=phone))
        db.commit()

        # 门店：30 家，分地形、时段、线路
        store_count = 0
        for i in range(1, 31):
            sid = f"S{i:03d}"
            if db.get(Store, sid) is not None:
                continue
            store_count += 1
            terrain = rng.choice(["normal", "normal", "normal", "mid", "mid", "strict"])
            tw = rng.choice(["AM", "PM", "any"])
            route_id = rng.choice([r[0] for r in ROUTES])
            store = Store(
                id=sid,
                name=f"门店{i:03d}号",
                address=f"模拟地址{i:03d}号",
                longitude=116.3 + rng.uniform(-0.2, 0.2),
                latitude=39.9 + rng.uniform(-0.15, 0.15),
                terrain_type=terrain,
                time_window=tw,
                priority=rng.randint(1, 9),
                enabled=True,
            )
            db.add(store)
            db.flush()
            db.add(StoreRouteMapping(store_id=sid, route_id=route_id, is_primary=True))
            # 交界门店：30% 概率有第二条线路
            if rng.random() < 0.3:
                other = rng.choice([r for r in [r[0] for r in ROUTES] if r != route_id])
                db.add(StoreRouteMapping(store_id=sid, route_id=other, is_primary=False))
        db.commit()

        # 车辆：4m2 * 28 / big * 3 / small * 9
        vdefs = [
            ("4m2", 630, 800, 2, 28, "4M2-{:03d}", "京A{:04d}", "全能去"),
            ("big", 300, 420, 2, 3, "BG-{:03d}", "京B{:04d}", "大小包能去"),
            ("small", 1, 300, 4, 9, "SM-{:03d}", "京C{:04d}", "小包能去"),
        ]
        for vtype, min_load, max_load, trips, count, id_tmpl, plate_tmpl, _cap_desc in vdefs:
            for i in range(1, count + 1):
                vid = id_tmpl.format(i)
                if db.get(Vehicle, vid) is None:
                    vehicle = Vehicle(
                        id=vid,
                        plate=plate_tmpl.format(i),
                        vehicle_type=vtype,
                        min_load=min_load,
                        max_load=max_load,
                        max_trips_per_day=trips,
                        driver_id=rng.choice([d[0] for d in DRIVERS]) if rng.random() < 0.6 else None,
                        warehouse_id="W01",
                        status="available",
                        enabled=True,
                    )
                    db.add(vehicle)
                    db.flush()
                    # 地形能力
                    if vtype == "4m2":
                        caps = {"normal": True, "mid": True, "strict": True}
                    elif vtype == "big":
                        caps = {"normal": True, "mid": True, "strict": False}
                    else:
                        caps = {"normal": True, "mid": True, "strict": True}
                    for terrain, can in caps.items():
                        db.add(VehicleTerrainCapability(
                            vehicle_id=vid, terrain_type=terrain, can_access=can,
                        ))
        db.commit()

        # 地形规则
        terrain_defs = [
            ("normal", "普通地形，所有车型可去", ["4m2", "big", "small"]),
            ("mid", "中控地形，大小包可去", ["big", "small"]),
            ("strict", "严控地形，仅小包可去", ["small"]),
        ]
        for t, desc, allows in terrain_defs:
            if db.get(TerrainRule, t) is None:
                db.add(TerrainRule(id=t, terrain_type=t, description=desc, allowed_vehicle_types=allows))
        db.commit()

        # 趟次规则
        trip_defs = [
            ("4m2", 2, 1, 1),
            ("big", 2, 1, 1),
            ("small", 4, 2, 2),
        ]
        for vt, daily, am, pm in trip_defs:
            if db.get(TripRule, vt) is None:
                db.add(TripRule(id=vt, vehicle_type=vt, daily_trips=daily, am_trips=am, pm_trips=pm))
        db.commit()

        # 装载规则
        load_defs = [
            ("4m2", 630, 800),
            ("big", 300, 420),
            ("small", 1, 300),
        ]
        for vt, mn, mx in load_defs:
            if db.get(LoadRule, vt) is None:
                db.add(LoadRule(id=vt, vehicle_type=vt, min_load=mn, max_load=mx))
        db.commit()

        # 默认约束配置 v1
        if db.query(ConstraintConfig).filter(ConstraintConfig.version == "v1").first() is None:
            cfg = ConstraintConfig(
                version="v1",
                name="默认约束配置",
                description="车辆智能调度 Agent 默认规则集",
                hard_constraints={
                    "vehicle_profiles": {
                        "4m2": {"min_load": 630, "max_load": 800, "am_trips": 1, "pm_trips": 1, "daily": 2},
                        "big": {"min_load": 300, "max_load": 420, "am_trips": 1, "pm_trips": 1, "daily": 2},
                        "small": {"min_load": 1, "max_load": 300, "am_trips": 2, "pm_trips": 2, "daily": 4},
                    },
                    "terrain_allows": {
                        "normal": ["4m2", "big", "small"],
                        "mid": ["big", "small"],
                        "strict": ["small"],
                    },
                    "time_window_rule": {"AM": "AM", "PM": "PM", "any": "AM"},
                    "min_load_to_dispatch": True,
                    "max_trips_per_day": True,
                },
                soft_constraints={
                    "priority_4m2": True,
                    "guarantee_big_small_trips": True,
                    "dynamic_fleet_size": True,
                },
                weights={
                    "w_4m2_usage": 0.30,
                    "w_load_rate": 0.25,
                    "w_trip_achievement": 0.25,
                    "w_cost": 0.10,
                    "w_soft_penalty": 0.10,
                },
                is_active=True,
            )
            db.add(cfg)
        db.commit()

        # 为门店在 store 表预留 demand 字段：用 extra 不可行，改为 demands 单独存内存（演示时实时生成）
        # 实际生产：货量来自 OMS 接口，存 store_demand 表（本演示简化）。

    print(f"种子数据写入完成。门店新增 {store_count} 家，车辆 28+3+9 台，规则配置 v1 已激活。")
    print("提示：调度任务运行时会在 data_perception 节点为每个门店生成随机 demand。")


# ---------------- RBAC 种子数据 ----------------

# (code, name, module)
_PERMISSIONS = [
    # 系统管理
    ("system:user:list", "用户查询", "system"),
    ("system:user:create", "用户新增", "system"),
    ("system:user:update", "用户编辑", "system"),
    ("system:user:delete", "用户删除", "system"),
    ("system:user:reset", "重置密码", "system"),
    ("system:role:list", "角色查询", "system"),
    ("system:role:create", "角色新增", "system"),
    ("system:role:update", "角色编辑", "system"),
    ("system:role:delete", "角色删除", "system"),
    ("system:permission:list", "权限查询", "system"),
    ("system:permission:create", "权限新增", "system"),
    ("system:permission:update", "权限编辑", "system"),
    ("system:permission:delete", "权限删除", "system"),
    ("system:menu:list", "菜单查询", "system"),
    ("system:menu:create", "菜单新增", "system"),
    ("system:menu:update", "菜单编辑", "system"),
    ("system:menu:delete", "菜单删除", "system"),
    ("system:dept:list", "部门查询", "system"),
    ("system:dept:create", "部门新增", "system"),
    ("system:dept:update", "部门编辑", "system"),
    ("system:dept:delete", "部门删除", "system"),
    ("system:dict:list", "字典查询", "system"),
    ("system:dict:create", "字典新增", "system"),
    ("system:dict:update", "字典编辑", "system"),
    ("system:dict:delete", "字典删除", "system"),
    ("system:param:list", "参数查询", "system"),
    ("system:param:create", "参数新增", "system"),
    ("system:param:update", "参数编辑", "system"),
    ("system:param:delete", "参数删除", "system"),
    ("system:log:list", "日志查询", "system"),
    ("system:log:delete", "日志删除", "system"),
    # 业务模块
    ("business:task:list", "任务查询", "business"),
    ("business:task:create", "任务创建", "business"),
    ("business:task:confirm", "方案确认", "business"),
    ("business:task:replan", "重新规划", "business"),
    ("business:store:list", "门店查询", "business"),
    ("business:store:create", "门店新增", "business"),
    ("business:store:update", "门店编辑", "business"),
    ("business:store:delete", "门店删除", "business"),
    ("business:vehicle:list", "车辆查询", "business"),
    ("business:vehicle:create", "车辆新增", "business"),
    ("business:vehicle:update", "车辆编辑", "business"),
    ("business:vehicle:delete", "车辆删除", "business"),
    ("business:route:list", "线路查询", "business"),
    ("business:route:create", "线路新增", "business"),
    ("business:route:update", "线路编辑", "business"),
    ("business:route:delete", "线路删除", "business"),
    ("business:rule:list", "规则查询", "business"),
    ("business:rule:update", "规则编辑", "business"),
    ("business:report:list", "报表查询", "business"),
]


def _build_menu_tree() -> list[dict]:
    """返回扁平菜单列表（含固定 id 便于角色分配）。"""
    menus = [
        # 一级目录
        {"id": "m-dashboard", "name": "工作台", "path": "/dashboard", "component": "DashboardView", "icon": "DashboardOutlined", "type": "menu", "sort": 1},
        {"id": "m-business", "name": "调度业务", "path": "/business", "component": "", "icon": "CarryOutOutlined", "type": "catalog", "sort": 2},
        {"id": "m-system", "name": "系统管理", "path": "/system", "component": "", "icon": "SettingOutlined", "type": "catalog", "sort": 3},
        # 业务子菜单
        {"id": "m-tasks", "parent_id": "m-business", "name": "调度任务", "path": "/tasks", "component": "TasksView", "type": "menu", "sort": 1},
        {"id": "m-stores", "parent_id": "m-business", "name": "门店管理", "path": "/stores", "component": "StoresView", "type": "menu", "sort": 2},
        {"id": "m-vehicles", "parent_id": "m-business", "name": "车辆管理", "path": "/vehicles", "component": "VehiclesView", "type": "menu", "sort": 3},
        {"id": "m-routes", "parent_id": "m-business", "name": "线路管理", "path": "/routes", "component": "RoutesView", "type": "menu", "sort": 4},
        {"id": "m-rules", "parent_id": "m-business", "name": "规则配置", "path": "/rules", "component": "RulesView", "type": "menu", "sort": 5},
        {"id": "m-reports", "parent_id": "m-business", "name": "报表中心", "path": "/reports", "component": "ReportsView", "type": "menu", "sort": 6},
        # 系统子菜单
        {"id": "m-users", "parent_id": "m-system", "name": "用户管理", "path": "/system/users", "component": "system/UsersView", "type": "menu", "sort": 1},
        {"id": "m-roles", "parent_id": "m-system", "name": "角色管理", "path": "/system/roles", "component": "system/RolesView", "type": "menu", "sort": 2},
        {"id": "m-perms", "parent_id": "m-system", "name": "权限管理", "path": "/system/permissions", "component": "system/PermissionsView", "type": "menu", "sort": 3},
        {"id": "m-menus", "parent_id": "m-system", "name": "菜单管理", "path": "/system/menus", "component": "system/MenusView", "type": "menu", "sort": 4},
        {"id": "m-depts", "parent_id": "m-system", "name": "部门管理", "path": "/system/depts", "component": "system/DeptsView", "type": "menu", "sort": 5},
        {"id": "m-dicts", "parent_id": "m-system", "name": "字典管理", "path": "/system/dicts", "component": "system/DictsView", "type": "menu", "sort": 6},
        {"id": "m-params", "parent_id": "m-system", "name": "参数管理", "path": "/system/params", "component": "system/ParamsView", "type": "menu", "sort": 7},
        {"id": "m-logs", "parent_id": "m-system", "name": "日志管理", "path": "/system/logs", "component": "system/LogsView", "type": "menu", "sort": 8},
    ]
    return menus


def ensure_rbac_seed() -> None:
    """初始化 RBAC 基础数据：部门/权限/菜单/角色/超管。幂等。"""
    with SessionLocal() as db:
        # 部门
        if db.query(Dept).count() == 0:
            root = Dept(id="dept-root", name="总公司", code="ROOT", sort=0)
            db.add(root)
            db.add(Dept(id="dept-dispatch", name="调度中心", code="DISPATCH", parent_id="dept-root", sort=1))
            db.add(Dept(id="dept-ops", name="运营部", code="OPS", parent_id="dept-root", sort=2))
            db.add(Dept(id="dept-it", name="信息技术部", code="IT", parent_id="dept-root", sort=3))
            db.commit()

        # 权限
        perm_by_code: dict[str, Permission] = {}
        for code, name, module in _PERMISSIONS:
            p = db.query(Permission).filter(Permission.code == code).first()
            if not p:
                p = Permission(id=f"perm-{code}", code=code, name=name, module=module)
                db.add(p)
                db.flush()
            perm_by_code[code] = p
        db.commit()

        # 菜单
        for m in _build_menu_tree():
            existing = db.get(Menu, m["id"])
            if existing:
                continue
            db.add(Menu(
                id=m["id"],
                parent_id=m.get("parent_id"),
                name=m["name"],
                path=m.get("path"),
                component=m.get("component"),
                icon=m.get("icon"),
                type=m.get("type", "menu"),
                sort=m.get("sort", 0),
                visible=True,
            ))
        db.commit()

        # 角色：admin / dispatcher / viewer
        def get_or_create_role(code: str, name: str, data_scope: str, description: str) -> Role:
            r = db.query(Role).filter(Role.code == code).first()
            if not r:
                r = Role(id=f"role-{code}", code=code, name=name, data_scope=data_scope, description=description, sort=0)
                db.add(r)
                db.flush()
            return r

        admin_role = get_or_create_role("admin", "系统管理员", "all", "拥有系统全部权限")
        dispatcher_role = get_or_create_role("dispatcher", "调度员", "all", "负责日常调度业务")
        viewer_role = get_or_create_role("viewer", "只读用户", "self", "仅可查看业务数据")

        # 角色权限分配（幂等）
        def sync_perms(role: Role, codes: list[str]) -> None:
            wanted = {perm_by_code[c].id for c in codes if c in perm_by_code}
            current = {p.id for p in role.permissions}
            if wanted != current:
                role.permissions = [perm_by_code[c] for c in codes if c in perm_by_code]

        sync_perms(admin_role, [c for c, _, _ in _PERMISSIONS])
        sync_perms(dispatcher_role, [c for c, _, _ in _PERMISSIONS if c.startswith("business:")])
        sync_perms(viewer_role, [c for c, _, _ in _PERMISSIONS if c.endswith(":list") and c.startswith("business:")])

        # 角色菜单分配
        all_menu_ids = [m["id"] for m in _build_menu_tree()]
        business_menu_ids = [m["id"] for m in _build_menu_tree() if m["id"] in (
            "m-dashboard", "m-business", "m-tasks", "m-stores", "m-vehicles", "m-routes", "m-rules", "m-reports"
        )]

        def sync_menus(role: Role, menu_ids: list[str]) -> None:
            wanted = set(menu_ids)
            current = {m.id for m in role.menus}
            if wanted != current:
                role.menus = db.query(Menu).filter(Menu.id.in_(menu_ids)).all()

        sync_menus(admin_role, all_menu_ids)
        sync_menus(dispatcher_role, business_menu_ids)
        sync_menus(viewer_role, business_menu_ids)

        # 超管账号
        admin_user = db.query(User).filter(User.username == settings.super_admin_username).first()
        if not admin_user:
            admin_user = User(
                id="user-admin",
                username=settings.super_admin_username,
                nickname="超级管理员",
                hashed_password=hash_password(settings.super_admin_password),
                is_super=True,
                enabled=True,
                dept_id="dept-it",
            )
            db.add(admin_user)
        elif not admin_user.is_super:
            admin_user.is_super = True
        db.commit()

        # 为 admin 角色绑定超管（便于界面展示）
        if admin_role not in admin_user.roles:
            admin_user.roles.append(admin_role)
        db.commit()

        # 演示账号：dispatcher / viewer
        for uname, nick, role_obj, dept_id in [
            ("dispatcher", "调度员小张", dispatcher_role, "dept-dispatch"),
            ("viewer", " viewer 小李", viewer_role, "dept-ops"),
        ]:
            u = db.query(User).filter(User.username == uname).first()
            if not u:
                u = User(
                    id=f"user-{uname}",
                    username=uname,
                    nickname=nick.strip(),
                    hashed_password=hash_password(uname + "123"),
                    is_super=False,
                    enabled=True,
                    dept_id=dept_id,
                )
                db.add(u)
                db.flush()
                if role_obj not in u.roles:
                    u.roles.append(role_obj)
        db.commit()

        # ---------- 默认字典（数据源/数据项） ----------
        _DEFAULT_DICTS = [
            ("veh_type", "车辆类型", "车辆类型字典", [
                ("4m2", "4m2", 1, "中型厢式"),
                ("big", "big", 2, "大型车"),
                ("small", "small", 3, "小型车"),
            ]),
            ("terrain", "地形类型", "门店地形字典", [
                ("普通", "normal", 1, "普通地形"),
                ("中控", "mid", 2, "中控地形"),
                ("严控", "strict", 3, "严控地形"),
            ]),
            ("task_status", "任务状态", "调度任务状态字典", [
                ("待启动", "pending", 1, None),
                ("运行中", "running", 2, None),
                ("已完成", "done", 3, None),
                ("已失败", "failed", 4, None),
            ]),
            ("time_window", "时间窗", "配送时间窗字典", [
                ("上午", "AM", 1, None),
                ("下午", "PM", 2, None),
                ("任意", "any", 3, None),
            ]),
        ]
        for code, name, desc, items in _DEFAULT_DICTS:
            d = db.query(Dict).filter(Dict.code == code).first()
            if not d:
                d = Dict(id=f"dict-{code}", code=code, name=name, description=desc, enabled=True)
                db.add(d)
                db.flush()
            # 仅当字典下无数据项时补齐
            if not db.query(DictItem).filter(DictItem.dict_id == d.id).first():
                for label, value, sort, remark in items:
                    db.add(DictItem(
                        dict_id=d.id, label=label, value=value, sort=sort, enabled=True, remark=remark,
                    ))
        db.commit()

        # ---------- 默认系统参数 ----------
        _DEFAULT_PARAMS = [
            ("solver_time_limit", "求解器时限(秒)", "5", "number", "CP-SAT 单次求解最大时限"),
            ("max_replan_count", "最大重规划次数", "3", "number", "单任务允许重规划上限"),
            ("min_load_to_dispatch", "最低装载率开关", "true", "bool", "是否强制最低装载率"),
            ("priority_4m2", "4m2 优先开关", "true", "bool", "是否优先使用 4m2 车型"),
            ("ws_heartbeat_sec", "WebSocket 心跳(秒)", "15", "number", "前端 WS 心跳间隔"),
        ]
        for code, name, value, ptype, remark in _DEFAULT_PARAMS:
            if not db.query(SysParam).filter(SysParam.code == code).first():
                db.add(SysParam(
                    id=f"param-{code}", code=code, name=name, value=value, type=ptype, remark=remark, enabled=True,
                ))
        db.commit()

    print("RBAC 种子完成：超管 admin/admin123，调度员 dispatcher/dispatcher123，只读 viewer/viewer123")


if __name__ == "__main__":
    seed_all()
    ensure_rbac_seed()
