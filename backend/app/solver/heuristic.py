"""启发式求解：生成 A/B/C 三个方案。

业务约束回顾（来自技术方案）：
- 车型与趟次：四米二 2 趟（上午/下午各 1）；大包 2 趟（上午/下午各 1）；小包 4 趟（上午 2 / 下午 2）。
- 装载：四米二 630-800；大包 300-420；小包 1-300。
- 发车：达到最低装载量才发车。
- 时段：上午门店上午送，下午门店下午送。
- 地形：普通/中控/严控；车辆能力分全能去（4m2）/大小包能去（big）/小包能去（small）。
- 货量不足：优先保障大包、小包日出车次数。
- 车型优先：多种派车方案优先用四米二。
- 动态调节：不保障每天 28/3/9 台满勤。

启发式核心流程（按方案策略调整）：
1. 按门店 time_window 分上午组与下午组。
2. 按门店 terrain_type 过滤可用车型。
3. 按策略选择车辆：A 优先 4m2；B 优先小/大包控成本；C 优先保障大包小包趟次。
4. 贪心装车：按线路分组门店，按 vehicle min_load ~ max_load 范围装车，达到 min_load 即发车。
5. 输出 plan details + metrics。
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Any


VEHICLE_PROFILES = {
    "4m2": {"min_load": 630, "max_load": 800, "am_trips": 1, "pm_trips": 1, "daily": 2},
    "big": {"min_load": 300, "max_load": 420, "am_trips": 1, "pm_trips": 1, "daily": 2},
    "small": {"min_load": 1, "max_load": 300, "am_trips": 2, "pm_trips": 2, "daily": 4},
}

# 地形允许车型：normal 任意；mid 不允许 4m2 之外的限制；strict 只允许小包
TERRAIN_ALLOWS = {
    "normal": {"4m2", "big", "small"},
    "mid": {"big", "small"},  # 中控：大小包能去
    "strict": {"small"},  # 严控：小包能去
}

# 单位成本（元/趟）：用于成本方案
COST_PER_TRIP = {"4m2": 320, "big": 200, "small": 120}


def _group_stores(stores: list[dict], demands_by_store: dict[str, int]) -> dict[str, list[dict]]:
    """按 time_window 分组并标注 demand。"""

    def demand_of(s: dict) -> int:
        return int(demands_by_store.get(s["id"], 0) or 0)

    grouped: dict[str, list[dict]] = {"AM": [], "PM": []}
    for s in stores:
        if not s.get("enabled", True):
            continue
        d = demand_of(s)
        if d <= 0:
            continue
        item = {**s, "demand": d}
        tw = (s.get("time_window") or "any").upper()
        if tw == "AM":
            grouped["AM"].append(item)
        elif tw == "PM":
            grouped["PM"].append(item)
        else:
            # any：默认放入上午（也可平均拆分，这里简化）
            grouped["AM"].append(item)
    return grouped


def _available_vehicles(vehicles: list[dict]) -> dict[str, list[dict]]:
    by_type: dict[str, list[dict]] = defaultdict(list)
    for v in vehicles:
        if not v.get("enabled", True):
            continue
        if v.get("status") not in (None, "available"):
            continue
        by_type[v["vehicle_type"]].append(v)
    for k in by_type:
        by_type[k].sort(key=lambda v: v["id"])
    return by_type


def _vehicle_can_access(v: dict, terrain_type: str) -> bool:
    caps = v.get("terrain_capability") or {}
    if caps:
        return bool(caps.get(terrain_type, False))
    # 默认按车型推断
    return v["vehicle_type"] in TERRAIN_ALLOWS.get(terrain_type, set())


def _greedy_pack(
    stores: list[dict],
    vehicles: list[dict],
    vehicle_type: str,
    *,
    time_window: str,
    trip_capacity: int,
    min_load: int,
    max_trips_per_vehicle: int,
    prefer_4m2: bool = False,
) -> list[dict]:
    """对一组门店用一组车辆进行贪心装车。

    返回 detail 列表：vehicle_id / trip_no / store_ids / load_amount / sequence
    """
    details: list[dict] = []
    sorted_stores = sorted(stores, key=lambda s: (-s.get("priority", 5), -s["demand"]))
    remaining = list(sorted_stores)

    vehicle_idx = 0
    while remaining and vehicle_idx < len(vehicles):
        v = vehicles[vehicle_idx]
        for trip_no in range(1, max_trips_per_vehicle + 1):
            if not remaining:
                break
            # 贪心装车，直到达到 max_load 或剩余门店需求为 0
            loaded: list[dict] = []
            current_load = 0
            while remaining:
                s = remaining[0]
                if s["terrain_type"] not in TERRAIN_ALLOWS and not _vehicle_can_access(v, s["terrain_type"]):
                    # 该门店地形不允许，跳过本车，放到下一车
                    break
                if not _vehicle_can_access(v, s["terrain_type"]):
                    break
                if current_load + s["demand"] > trip_capacity:
                    # 当前车装不下，尝试下一个门店（小件可能装得下）
                    # 简化：要求每个门店 demand 不超过单趟容量
                    if s["demand"] > trip_capacity:
                        # 单门店需求超出单趟容量，拆分
                        take = trip_capacity - current_load
                        if take <= 0:
                            break
                        loaded.append({**s, "demand": take})
                        current_load += take
                        remaining[0] = {**s, "demand": s["demand"] - take}
                        continue
                    break
                loaded.append(s)
                current_load += s["demand"]
                remaining.pop(0)
            if loaded and current_load >= min_load:
                details.append(
                    {
                        "vehicle_id": v["id"],
                        "vehicle_type": vehicle_type,
                        "trip_no": trip_no,
                        "time_window": time_window,
                        "store_ids": [s["id"] for s in loaded],
                        "load_amount": current_load,
                        "sequence": len(details) + 1,
                    }
                )
            elif loaded:
                # 没达到最低装载量：货量不足保障规则
                # 若车型为小包/大包，仍允许发车以保障趟次
                if vehicle_type in ("small", "big") and current_load > 0:
                    details.append(
                        {
                            "vehicle_id": v["id"],
                            "vehicle_type": vehicle_type,
                            "trip_no": trip_no,
                            "time_window": time_window,
                            "store_ids": [s["id"] for s in loaded],
                            "load_amount": current_load,
                            "sequence": len(details) + 1,
                        }
                    )
                else:
                    # 放回 remaining
                    remaining = loaded + remaining
        vehicle_idx += 1
    return details


def _strategy_priority(strategy: str) -> list[str]:
    """根据策略返回车型优先级列表。"""
    if strategy == "4m2_priority":
        return ["4m2", "big", "small"]
    if strategy == "cost_min":
        # 小包最便宜，优先用；但要满足最低装载量约束，故顺序：small->big->4m2
        return ["small", "big", "4m2"]
    if strategy == "big_small_priority":
        # 优先保障大包/小包趟次
        return ["big", "small", "4m2"]
    return ["4m2", "big", "small"]


def _build_plan(
    snapshot: dict,
    strategy: str,
    plan_id: str,
    name: str,
    solver_type: str = "heuristic",
) -> dict:
    stores = snapshot.get("stores") or []
    vehicles = snapshot.get("vehicles") or []
    demands_list = snapshot.get("demands") or []
    demands_by_store = {d["store_id"]: int(d.get("demand", 0) or 0) for d in demands_list}

    grouped = _group_stores(stores, demands_by_store)
    by_type = _available_vehicles(vehicles)
    priority_types = _strategy_priority(strategy)

    details: list[dict] = []
    for time_window in ("AM", "PM"):
        bucket = grouped.get(time_window, [])
        if not bucket:
            continue
        # 按 terrain_type 二次分组
        by_terrain: dict[str, list[dict]] = defaultdict(list)
        for s in bucket:
            by_terrain[s.get("terrain_type", "normal")].append(s)
        for vtype in priority_types:
            trip_profile = VEHICLE_PROFILES[vtype]
            max_trips = (
                trip_profile["am_trips"] if time_window == "AM" else trip_profile["pm_trips"]
            )
            # 收集该车型能去的所有门店
            served_terrains = [
                t for t, stores_in_t in by_terrain.items()
                if vtype in TERRAIN_ALLOWS.get(t, set()) and stores_in_t
            ]
            if not served_terrains:
                continue
            store_pool = []
            for t in served_terrains:
                store_pool.extend(by_terrain[t])
                by_terrain[t] = []  # 标记已处理
            if not store_pool:
                continue
            vs = by_type.get(vtype, [])
            d = _greedy_pack(
                store_pool,
                vs,
                vtype,
                time_window=time_window,
                trip_capacity=trip_profile["max_load"],
                min_load=trip_profile["min_load"],
                max_trips_per_vehicle=max_trips,
            )
            details.extend(d)

    plan = _compose_plan(plan_id, name, strategy, solver_type, details, vehicles)
    return plan


def _compose_plan(
    plan_id: str,
    name: str,
    strategy: str,
    solver_type: str,
    details: list[dict],
    vehicles: list[dict],
) -> dict:
    total_load = sum(d["load_amount"] for d in details)
    total_trips = len(details)
    used_vehicle_ids = {d["vehicle_id"] for d in details}
    used_vehicles = len(used_vehicle_ids)
    # 平均装载率
    load_rates = []
    for d in details:
        max_load = VEHICLE_PROFILES.get(d["vehicle_type"], {}).get("max_load", 1)
        load_rates.append(d["load_amount"] / max_load if max_load else 0.0)
    avg_load_rate = round(sum(load_rates) / len(load_rates), 4) if load_rates else 0.0
    # 四米二使用率
    four_two_used = sum(1 for d in details if d["vehicle_type"] == "4m2")
    four_two_total = sum(1 for v in vehicles if v["vehicle_type"] == "4m2" and v.get("enabled", True))
    four_two_usage = round(four_two_used / four_two_total, 4) if four_two_total else 0.0
    # 大包/小包趟次达成率
    big_small_planned = 3 * 2 + 9 * 4  # 6 + 36 = 42
    big_small_actual = sum(1 for d in details if d["vehicle_type"] in ("big", "small"))
    big_small_achievement = round(big_small_actual / big_small_planned, 4) if big_small_planned else 0.0
    # 估算成本
    estimated_cost = float(sum(COST_PER_TRIP.get(d["vehicle_type"], 0) for d in details))

    return {
        "plan_id": plan_id,
        "name": name,
        "strategy": strategy,
        "solver_type": solver_type,
        "details": details,
        "total_load": total_load,
        "total_trips": total_trips,
        "used_vehicles": used_vehicles,
        "avg_load_rate": avg_load_rate,
        "four_two_usage": four_two_usage,
        "big_small_achievement": big_small_achievement,
        "estimated_cost": estimated_cost,
        "summary": {
            "used_vehicle_ids": sorted(used_vehicle_ids),
            "vehicle_type_breakdown": _count_by_type(details),
        },
    }


def _count_by_type(details: list[dict]) -> dict:
    counts: dict[str, int] = defaultdict(int)
    for d in details:
        counts[d["vehicle_type"]] += 1
    return dict(counts)


def generate_heuristic_plans(snapshot: dict, config: dict | None = None) -> list[dict]:
    """生成 A/B/C 三个启发式方案。"""
    return [
        _build_plan(snapshot, "4m2_priority", "A", "方案A：四米二优先（启发式）"),
        _build_plan(snapshot, "cost_min", "B", "方案B：成本最低（启发式）"),
        _build_plan(snapshot, "big_small_priority", "C", "方案C：大包/小包趟次保障优先（启发式）"),
    ]
