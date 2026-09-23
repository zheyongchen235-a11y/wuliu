"""LangGraph 状态定义。

对应技术方案 4.1 节 SchedulingState。
"""
from __future__ import annotations

from typing import Any, TypedDict


class SchedulingState(TypedDict, total=False):
    """调度工作流状态."""

    # 基本字段
    task_id: str
    tenant_id: str
    schedule_date: str
    time_window: str
    status: str

    # 数据快照
    stores: list[dict]
    vehicles: list[dict]
    routes: list[dict]
    store_route_mappings: list[dict]
    terrain_rules: list[dict]
    demands: list[dict]

    # 规则
    hard_constraints: dict
    soft_constraints: dict
    rule_version: str
    weights: dict

    # 校验
    validation_errors: list[str]
    validation_warnings: list[str]

    # 方案
    candidate_plans: list[dict]
    scored_plans: list[dict]
    selected_plan: dict | None
    plan_explanation: str | None

    # 人工确认
    confirmation: dict | None

    # 执行
    dispatch_result: dict | None

    # 异常与重排
    exception_events: list[dict]
    replan_count: int
    locked_trip_ids: list[str]
    replan_trigger: str | None

    # 报告
    report: str | None
    report_metrics: dict | None

    # LLM 消息记录
    messages: list[Any]
