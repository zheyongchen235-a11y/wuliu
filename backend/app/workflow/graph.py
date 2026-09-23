"""构建 LangGraph 调度工作流图.

对应技术方案 4.2 节工作流图：
START -> load_task -> data_perception -> constraint_parse -> rule_validation
rule_validation --(validation_errors)--> exception_handler -> END
rule_validation --(ok)--> plan_generation
plan_generation --(no candidate)--> relax_constraints -> plan_generation
plan_generation --(ok)--> plan_scoring -> plan_explanation -> human_confirmation
human_confirmation --(approved)--> dispatch_execution -> report_generation -> END
human_confirmation --(rejected)--> plan_generation
异常重排入口：exception_event -> monitor_exception -> impact_analysis -> replan
                -> plan_scoring -> human_confirmation -> dispatch_execution
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from ..database import SessionLocal
from ..models.scheduling import SchedulingTask
from . import nodes
from .checkpoint import make_checkpointer
from .state import SchedulingState

logger = logging.getLogger(__name__)


def build_graph():
    """构建并编译调度工作流图."""
    builder = StateGraph(SchedulingState)

    builder.add_node("load_task", nodes.load_task)
    builder.add_node("data_perception", nodes.data_perception)
    builder.add_node("constraint_parse", nodes.constraint_parse)
    builder.add_node("rule_validation", nodes.rule_validation)
    builder.add_node("plan_generation", nodes.plan_generation)
    builder.add_node("plan_scoring", nodes.plan_scoring)
    builder.add_node("plan_explanation", nodes.plan_explanation)
    builder.add_node("human_confirmation", nodes.human_confirmation)
    builder.add_node("dispatch_execution", nodes.dispatch_execution)
    builder.add_node("report_generation", nodes.report_generation)
    builder.add_node("exception_handler", nodes.exception_handler)
    builder.add_node("relax_constraints", nodes.relax_constraints)
    builder.add_node("monitor_exception", nodes.monitor_exception)
    builder.add_node("impact_analysis", nodes.impact_analysis)
    builder.add_node("replan", nodes.replan)

    builder.add_edge(START, "load_task")
    builder.add_edge("load_task", "data_perception")
    builder.add_edge("data_perception", "constraint_parse")
    builder.add_edge("constraint_parse", "rule_validation")

    builder.add_conditional_edges(
        "rule_validation",
        lambda s: "exception_handler" if s.get("validation_errors") else "plan_generation",
        {"exception_handler": "exception_handler", "plan_generation": "plan_generation"},
    )

    builder.add_conditional_edges(
        "plan_generation",
        lambda s: "plan_scoring" if s.get("candidate_plans") else "relax_constraints",
        {"plan_scoring": "plan_scoring", "relax_constraints": "relax_constraints"},
    )
    builder.add_edge("relax_constraints", "plan_generation")

    builder.add_edge("plan_scoring", "plan_explanation")
    builder.add_edge("plan_explanation", "human_confirmation")

    builder.add_conditional_edges(
        "human_confirmation",
        lambda s: "dispatch_execution" if (s.get("confirmation") or {}).get("approved") else "plan_generation",
        {"dispatch_execution": "dispatch_execution", "plan_generation": "plan_generation"},
    )

    builder.add_edge("dispatch_execution", "report_generation")
    builder.add_edge("report_generation", END)
    builder.add_edge("exception_handler", END)

    # 异常重排子流：monitor_exception -> impact_analysis -> replan -> plan_scoring
    builder.add_edge("monitor_exception", "impact_analysis")
    builder.add_edge("impact_analysis", "replan")
    builder.add_edge("replan", "plan_scoring")

    checkpointer = make_checkpointer()
    return builder.compile(checkpointer=checkpointer)


# 全局单例 graph
_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


async def run_scheduling(task_id: str, *, initial_state: dict | None = None) -> dict:
    """运行调度工作流.

    在 human_confirmation 节点会 interrupt，等待 /confirm 接口调用 Command(resume=...)。
    """
    graph = get_graph()
    config = {"configurable": {"thread_id": task_id}}
    init: dict[str, Any] = {"task_id": task_id, "status": "running"}
    if initial_state:
        init.update(initial_state)
    result = await graph.ainvoke(init, config=config)
    return result


async def resume_scheduling(task_id: str, payload: dict) -> dict:
    """人工确认后恢复工作流."""
    graph = get_graph()
    config = {"configurable": {"thread_id": task_id}}
    result = await graph.ainvoke(Command(resume=payload), config=config)
    return result
