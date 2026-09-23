"""方案评分与排序。

评分函数：
- 硬约束违规：直接淘汰（设为 0 分并标记）
- 软约束违规：扣分
- 总分 = w1 * 四米二使用率 + w2 * 平均装载率 + w3 * 大包/小包趟次达成
        - w4 * 成本（归一化） - w5 * 软约束违规惩罚
"""
from __future__ import annotations

from typing import Any

from .heuristic import VEHICLE_PROFILES, COST_PER_TRIP


def _normalize_cost(plans: list[dict]) -> dict[str, float]:
    """对成本做 min-max 归一化，成本越低得分越高。"""
    if not plans:
        return {}
    costs = [p.get("estimated_cost", 0) for p in plans]
    cmin, cmax = min(costs), max(costs)
    out: dict[str, float] = {}
    for p in plans:
        c = p.get("estimated_cost", 0)
        if cmax == cmin:
            out[p["plan_id"]] = 1.0
        else:
            # 1 - (c - cmin) / (cmax - cmin)
            out[p["plan_id"]] = 1.0 - (c - cmin) / (cmax - cmin)
    return out


def _check_hard_constraints(plan: dict, snapshot: dict) -> list[str]:
    """检查硬约束违规。返回违规说明列表。"""
    violations: list[str] = []
    details = plan.get("details") or []
    vehicles = {v["id"]: v for v in (snapshot.get("vehicles") or [])}
    stores = {s["id"]: s for s in (snapshot.get("stores") or [])}

    for d in details:
        v = vehicles.get(d["vehicle_id"])
        if v is None:
            continue
        profile = VEHICLE_PROFILES.get(d["vehicle_type"], {})
        # 装载上下限
        if d["load_amount"] > profile.get("max_load", d["load_amount"]):
            violations.append(
                f"车辆 {d['vehicle_id']} 趟次 {d['trip_no']} 超载: {d['load_amount']} > {profile.get('max_load')}"
            )
        # 地形能力
        for sid in d["store_ids"]:
            s = stores.get(sid, {})
            terrain = s.get("terrain_type", "normal")
            caps = v.get("terrain_capability") or {}
            if caps and not caps.get(terrain, False):
                violations.append(
                    f"车辆 {d['vehicle_id']} 不能去 {terrain} 地形门店 {sid}"
                )
        # 时段
        for sid in d["store_ids"]:
            s = stores.get(sid, {})
            tw = (s.get("time_window") or "any").upper()
            if tw in ("AM", "PM") and tw != d["time_window"]:
                violations.append(
                    f"门店 {sid} 时段 {tw} 与趟次时段 {d['time_window']} 不符"
                )

    return violations


def _check_soft_constraints(plan: dict, snapshot: dict) -> list[str]:
    """软约束违规：未达最低装载量（除小包外）、趟次数未达成等。"""
    violations: list[str] = []
    details = plan.get("details") or []
    for d in details:
        profile = VEHICLE_PROFILES.get(d["vehicle_type"], {})
        min_load = profile.get("min_load", 0)
        if d["load_amount"] < min_load and d["vehicle_type"] != "small":
            violations.append(
                f"车辆 {d['vehicle_id']} 趟次 {d['trip_no']} 未达最低装载量: "
                f"{d['load_amount']} < {min_load}"
            )
    return violations


def score_plan(plan: dict, snapshot: dict, weights: dict | None = None) -> dict:
    """对单个方案评分。"""
    weights = weights or {
        "w_4m2_usage": 0.30,
        "w_load_rate": 0.25,
        "w_trip_achievement": 0.25,
        "w_cost": 0.10,
        "w_soft_penalty": 0.10,
    }
    hard_violations = _check_hard_constraints(plan, snapshot)
    soft_violations = _check_soft_constraints(plan, snapshot)

    w1 = weights.get("w_4m2_usage", 0.30)
    w2 = weights.get("w_load_rate", 0.25)
    w3 = weights.get("w_trip_achievement", 0.25)
    w4 = weights.get("w_cost", 0.10)
    w5 = weights.get("w_soft_penalty", 0.10)

    score_4m2 = float(plan.get("four_two_usage", 0.0))
    score_load = float(plan.get("avg_load_rate", 0.0))
    score_trip = float(plan.get("big_small_achievement", 0.0))
    # 成本项需要归一化，但单方案评分时使用 1 - cost/max_possible
    max_cost = sum(COST_PER_TRIP.values()) * 30  # 上限近似
    score_cost = max(0.0, 1.0 - float(plan.get("estimated_cost", 0)) / max_cost) if max_cost else 0.0
    score_soft_penalty = -min(1.0, len(soft_violations) / 10.0)

    if hard_violations:
        total = 0.0
    else:
        total = (
            w1 * score_4m2
            + w2 * score_load
            + w3 * score_trip
            + w4 * score_cost
            + w5 * score_soft_penalty
        )
        total = max(0.0, min(1.0, total))

    return {
        "total_score": round(total, 4),
        "score_4m2_usage": round(score_4m2, 4),
        "score_load_rate": round(score_load, 4),
        "score_trip_achievement": round(score_trip, 4),
        "score_cost": round(score_cost, 4),
        "score_soft_penalty": round(score_soft_penalty, 4),
        "hard_constraint_violations": hard_violations,
        "soft_constraint_violations": soft_violations,
    }


def rank_plans(plans: list[dict]) -> list[dict]:
    """按 total_score 降序排序；同分按四米二使用率、装载率降序。"""

    def key(p: dict):
        s = p.get("score") or {}
        return (
            s.get("total_score", 0.0),
            s.get("score_4m2_usage", 0.0),
            s.get("score_load_rate", 0.0),
        )

    return sorted(plans, key=key, reverse=True)
