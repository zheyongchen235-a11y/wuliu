"""LangGraph 工作流节点实现.

对应技术方案 4.3 节：load_task / data_perception / constraint_parse /
rule_validation / plan_generation / plan_scoring / plan_explanation /
human_confirmation / dispatch_execution / report_generation /
exception_handler / relax_constraints / monitor_exception /
impact_analysis / replan.

每个节点为 async 函数，输入输出均为 SchedulingState（局部更新）。
节点内部通过 SessionLocal 直接操作数据库；通过 publish_progress 推送 WebSocket。
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from langgraph.types import interrupt

from ..database import SessionLocal
from ..llm.explainer import explain_plan, generate_report
from ..models.rules import ConstraintConfig
from ..models.scheduling import SchedulingTask
from ..services import scheduling as sched_service
from ..services import rules as rules_service
from ..solver import generate_plans
from .state import SchedulingState

logger = logging.getLogger(__name__)


# ---------------- 工具函数 ----------------

async def _publish(state: SchedulingState, *, node: str, status: str, message: str, progress: int, extra: dict | None = None) -> None:
    await sched_service.publish_progress(
        state.get("task_id", ""),
        node=node,
        status=status,
        message=message,
        progress=progress,
        extra=extra or {},
    )


def _sync_publish(state: SchedulingState, *, node: str, status: str, message: str, progress: int, extra: dict | None = None) -> None:
    """同步推送 WebSocket（在 sync 节点里调用）。"""
    try:
        asyncio.get_event_loop().create_task(
            sched_service.publish_progress(
                state.get("task_id", ""),
                node=node, status=status, message=message, progress=progress, extra=extra or {},
            )
        )
    except RuntimeError:
        pass


# ---------------- 节点 ----------------

async def load_task(state: SchedulingState) -> dict:
    """加载任务、租户、日期、时间窗."""
    task_id = state.get("task_id", "")
    await _publish(state, node="load_task", status="running", message="加载调度任务...", progress=5)
    with SessionLocal() as db:
        task = sched_service.get_task(db, task_id)
        if task is None:
            return {"validation_errors": [f"任务 {task_id} 不存在"], "status": "failed"}
        # 在 session 内提取字段，避免 detached 访问
        task_data = {
            "tenant_id": task.tenant_id,
            "schedule_date": task.schedule_date.isoformat(),
            "time_window": task.time_window,
            "rule_version": task.rule_version,
            "replan_count": task.replan_count,
        }
        sched_service.update_task_status(db, task_id, status="running", current_node="load_task")
    await _publish(state, node="load_task", status="done", message="任务已加载", progress=10)
    return {**task_data, "status": "running"}


async def data_perception(state: SchedulingState) -> dict:
    """拉取门店、车辆、线路、地形、货量、规则."""
    await _publish(state, node="data_perception", status="running", message="感知调度数据...", progress=20)
    task_id = state["task_id"]
    with SessionLocal() as db:
        snapshot = sched_service.snapshot_task_data(db, task_id)
        # 在 session 内取所有需要的字段（避免 detached 访问）
        snap_data = {
            "stores": list(snapshot.stores or []),
            "vehicles": list(snapshot.vehicles or []),
            "routes": list(snapshot.routes or []),
            "store_route_mappings": list(snapshot.store_route_mappings or []),
            "terrain_rules": list(snapshot.terrain_rules or []),
            "demands": list(snapshot.demands or []),
        }
        # 规则快照
        if state.get("rule_version"):
            cfg = rules_service.get_constraint_config_by_version(db, state["rule_version"])
        else:
            cfg = rules_service.get_active_constraint_config(db)
        hard = dict(cfg.hard_constraints or {}) if cfg else {}
        soft = dict(cfg.soft_constraints or {}) if cfg else {}
        weights = dict(cfg.weights or {}) if cfg else {}
        rule_version = cfg.version if cfg else state.get("rule_version")
        if cfg:
            rules_service.create_constraint_snapshot(db, task_id=task_id, config=cfg)
    store_count = len(snap_data["stores"])
    vehicle_count = len(snap_data["vehicles"])
    await _publish(state, node="data_perception", status="done",
                   message=f"数据已感知：{store_count} 门店 / {vehicle_count} 车辆",
                   progress=30, extra={"store_count": store_count, "vehicle_count": vehicle_count})
    return {
        **snap_data,
        "hard_constraints": hard,
        "soft_constraints": soft,
        "weights": weights,
        "rule_version": rule_version,
    }


async def constraint_parse(state: SchedulingState) -> dict:
    """规则中心配置解析为硬/软约束."""
    await _publish(state, node="constraint_parse", status="running", message="解析规则约束...", progress=40)
    hard = state.get("hard_constraints") or {}
    soft = state.get("soft_constraints") or {}
    # 默认补充：车型趟次/装载/地形规则
    hard.setdefault("vehicle_profiles", {
        "4m2": {"min_load": 630, "max_load": 800, "am_trips": 1, "pm_trips": 1, "daily": 2},
        "big": {"min_load": 300, "max_load": 420, "am_trips": 1, "pm_trips": 1, "daily": 2},
        "small": {"min_load": 1, "max_load": 300, "am_trips": 2, "pm_trips": 2, "daily": 4},
    })
    hard.setdefault("terrain_allows", {
        "normal": ["4m2", "big", "small"],
        "mid": ["big", "small"],
        "strict": ["small"],
    })
    hard.setdefault("time_window_rule", {"AM": "AM", "PM": "PM", "any": "AM"})
    soft.setdefault("priority_4m2", True)
    soft.setdefault("guarantee_big_small_trips", True)
    await _publish(state, node="constraint_parse", status="done", message="规则解析完成", progress=45)
    return {"hard_constraints": hard, "soft_constraints": soft}


async def rule_validation(state: SchedulingState) -> dict:
    """校验数据完整性、规则冲突、地形冲突."""
    await _publish(state, node="rule_validation", status="running", message="校验数据与规则...", progress=50)
    errors: list[str] = []
    warnings: list[str] = []

    stores = state.get("stores") or []
    vehicles = state.get("vehicles") or []
    demands = state.get("demands") or []
    demands_by_store = {d["store_id"]: int(d.get("demand", 0) or 0) for d in demands}

    if not stores:
        errors.append("无可用门店数据")
    if not vehicles:
        errors.append("无可用车辆数据")
    if not any(demands_by_store.values()):
        warnings.append("当日货量均为 0，调度结果可能无意义")

    # 门店地形必须存在可服务车型
    terrain_allows = (state.get("hard_constraints") or {}).get("terrain_allows") or {}
    for s in stores:
        t = s.get("terrain_type", "normal")
        allowed = terrain_allows.get(t, [])
        capable_vehicles = [v for v in vehicles if v["vehicle_type"] in allowed and v.get("enabled", True)]
        if not capable_vehicles:
            errors.append(f"门店 {s['id']} 地形 {t} 无可用车型")

    if errors:
        await _publish(state, node="rule_validation", status="error",
                       message=f"校验失败：{len(errors)} 处错误", progress=50, extra={"errors": errors})
    else:
        await _publish(state, node="rule_validation", status="done",
                       message=f"校验通过（{len(warnings)} 处提醒）", progress=55, extra={"warnings": warnings})
    return {"validation_errors": errors, "validation_warnings": warnings}


async def plan_generation(state: SchedulingState) -> dict:
    """调用求解器生成多方案."""
    await _publish(state, node="plan_generation", status="running", message="正在生成方案 A/B/C/D...", progress=60)
    snapshot = {
        "stores": state.get("stores") or [],
        "vehicles": state.get("vehicles") or [],
        "routes": state.get("routes") or [],
        "store_route_mappings": state.get("store_route_mappings") or [],
        "terrain_rules": state.get("terrain_rules") or [],
        "demands": state.get("demands") or [],
    }
    config = {
        "hard_constraints": state.get("hard_constraints") or {},
        "soft_constraints": state.get("soft_constraints") or {},
        "weights": state.get("weights") or {},
    }
    # 在线程池中跑求解器（CP-SAT 可能阻塞）
    plans = await asyncio.to_thread(generate_plans, snapshot, config)
    await _publish(state, node="plan_generation", status="done",
                   message=f"生成 {len(plans)} 个候选方案",
                   progress=70, extra={"plan_ids": [p["plan_id"] for p in plans]})
    return {"candidate_plans": plans, "scored_plans": plans}


async def plan_scoring(state: SchedulingState) -> dict:
    """方案评分（已在 solver 内完成，这里仅排序+持久化）."""
    await _publish(state, node="plan_scoring", status="running", message="方案评分中...", progress=75)
    plans = state.get("scored_plans") or []
    plans_sorted = sorted(plans, key=lambda p: (p.get("score") or {}).get("total_score", 0), reverse=True)
    with SessionLocal() as db:
        sched_service.save_plans(db, state["task_id"], plans_sorted)
    await _publish(state, node="plan_scoring", status="done",
                   message=f"评分完成，推荐方案 {plans_sorted[0]['plan_id'] if plans_sorted else 'N/A'}",
                   progress=80)
    return {"scored_plans": plans_sorted}


async def plan_explanation(state: SchedulingState) -> dict:
    """LLM 生成自然语言解释."""
    await _publish(state, node="plan_explanation", status="running", message="生成方案解释...", progress=82)
    plans = state.get("scored_plans") or []
    explanation = await explain_plan(plans, state)
    await _publish(state, node="plan_explanation", status="done", message="解释生成完成", progress=85)
    return {"plan_explanation": explanation}


async def human_confirmation(state: SchedulingState) -> dict:
    """中断等待人工确认."""
    await _publish(state, node="human_confirmation", status="awaiting_confirmation",
                   message="等待调度员确认方案...", progress=88)
    with SessionLocal() as db:
        sched_service.update_task_status(db, state["task_id"], status="awaiting_confirmation",
                                         current_node="human_confirmation")
    plans = state.get("scored_plans") or []
    recommended = plans[0] if plans else None
    decision = interrupt({
        "task_id": state.get("task_id"),
        "plans": [{"plan_id": p["plan_id"], "name": p["name"], "score": p.get("score", {})} for p in plans],
        "recommended": recommended["plan_id"] if recommended else None,
        "explanation": state.get("plan_explanation"),
    })
    return {"confirmation": decision}


async def dispatch_execution(state: SchedulingState) -> dict:
    """下发 TMS / 司机端，写执行记录."""
    await _publish(state, node="dispatch_execution", status="running", message="下发方案至 TMS...", progress=92)
    confirmation = state.get("confirmation") or {}
    plan_id = confirmation.get("plan_id")
    plans = state.get("scored_plans") or []
    selected = next((p for p in plans if p["plan_id"] == plan_id), None)
    if selected is None:
        return {"dispatch_result": {"status": "failed", "error": "未找到所选方案"}}
    from ..services.execution import dispatch_to_tms
    result = await dispatch_to_tms(state["task_id"], selected)
    await _publish(state, node="dispatch_execution", status="done",
                   message=f"下发完成：dispatch_id={result.get('dispatch_id')}", progress=95,
                   extra=result)
    return {"dispatch_result": result, "selected_plan": selected}


async def report_generation(state: SchedulingState) -> dict:
    """生成调度报告."""
    await _publish(state, node="report_generation", status="running", message="生成调度报告...", progress=97)
    report_text, metrics = await generate_report(state)
    with SessionLocal() as db:
        sched_service.save_report(db, state["task_id"],
                                  report_type="task_summary",
                                  content=report_text, metrics=metrics)
        sched_service.update_task_status(db, state["task_id"], status="completed",
                                         current_node="report_generation")
    await _publish(state, node="report_generation", status="done", message="报告生成完成", progress=100)
    return {"report": report_text, "report_metrics": metrics, "status": "completed"}


async def exception_handler(state: SchedulingState) -> dict:
    """异常分支终止."""
    errors = state.get("validation_errors") or []
    msg = "; ".join(errors)
    with SessionLocal() as db:
        sched_service.update_task_status(db, state["task_id"], status="failed",
                                         current_node="exception_handler",
                                         error_message=msg)
    await _publish(state, node="exception_handler", status="error", message=f"调度失败：{msg}", progress=100)
    return {"status": "failed"}


async def relax_constraints(state: SchedulingState) -> dict:
    """放宽软约束后重试."""
    await _publish(state, node="relax_constraints", status="running", message="放宽软约束重试...", progress=65)
    soft = dict(state.get("soft_constraints") or {})
    soft["guarantee_big_small_trips"] = False
    soft["priority_4m2"] = False
    return {"soft_constraints": soft}


async def monitor_exception(state: SchedulingState) -> dict:
    """接收异常事件（来自 MQ / API）."""
    events = state.get("exception_events") or []
    await _publish(state, node="monitor_exception", status="running",
                   message=f"处理 {len(events)} 个异常事件", progress=50)
    return {}


async def impact_analysis(state: SchedulingState) -> dict:
    """分析异常影响范围."""
    events = state.get("exception_events") or []
    affected_vehicles = set()
    affected_stores = set()
    for e in events:
        affected_vehicles.update(e.get("affected_vehicle_ids") or [])
        affected_stores.update(e.get("affected_store_ids") or [])
    await _publish(state, node="impact_analysis", status="done",
                   message=f"影响范围：{len(affected_vehicles)} 车 / {len(affected_stores)} 门店",
                   progress=55,
                   extra={"vehicles": list(affected_vehicles), "stores": list(affected_stores)})
    return {}


async def replan(state: SchedulingState) -> dict:
    """锁定已执行趟次，局部 / 全局重排."""
    await _publish(state, node="replan", status="running", message="重排调度方案...", progress=60)
    replan_count = state.get("replan_count", 0) + 1
    if replan_count > 3:
        await _publish(state, node="replan", status="error", message="超过最大重排次数", progress=100)
        return {"status": "failed"}
    # 简化：清空候选方案并重新生成（生产应锁定已执行趟次）
    snapshot = {
        "stores": state.get("stores") or [],
        "vehicles": state.get("vehicles") or [],
        "routes": state.get("routes") or [],
        "store_route_mappings": state.get("store_route_mappings") or [],
        "terrain_rules": state.get("terrain_rules") or [],
        "demands": state.get("demands") or [],
    }
    config = {
        "hard_constraints": state.get("hard_constraints") or {},
        "soft_constraints": state.get("soft_constraints") or {},
        "weights": state.get("weights") or {},
    }
    plans = await asyncio.to_thread(generate_plans, snapshot, config)
    with SessionLocal() as db:
        sched_service.save_plans(db, state["task_id"], plans)
        sched_service.update_task_status(db, state["task_id"], status="awaiting_confirmation",
                                         current_node="replan", replan_count=replan_count)
    return {"candidate_plans": plans, "scored_plans": plans, "replan_count": replan_count}
