"""LLM 解释与报告生成.

为避免强依赖外部 LLM API，默认使用规则化 mock。
若配置 SCHED_LLM_PROVIDER != mock，则通过 langchain_openai.ChatOpenAI 调用真实模型
（支持 OpenAI / DeepSeek / 通义千问等 OpenAI 兼容接口）。
"""
from __future__ import annotations

import logging
from typing import Any

from ..config import settings

logger = logging.getLogger(__name__)


def _format_plan_brief(plan: dict) -> str:
    score = plan.get("score") or {}
    return (
        f"方案 {plan['plan_id']}（{plan['name']}）："
        f"综合评分 {score.get('total_score', 0):.4f}，"
        f"使用车辆 {plan.get('used_vehicles', 0)} 台 / "
        f"{plan.get('total_trips', 0)} 趟，"
        f"平均装载率 {plan.get('avg_load_rate', 0):.2%}，"
        f"四米二使用率 {plan.get('four_two_usage', 0):.2%}，"
        f"大包/小包趟次达成率 {plan.get('big_small_achievement', 0):.2%}，"
        f"估算成本 ¥{plan.get('estimated_cost', 0):.0f}。"
    )


def _mock_explain(plans: list[dict]) -> str:
    """规则化兜底解释。"""
    lines: list[str] = []
    lines.append(f"本次调度共生成 {len(plans)} 个候选方案，按综合评分排序如下：")
    lines.append("")
    for i, p in enumerate(plans, 1):
        lines.append(f"{i}. {_format_plan_brief(p)}")
        score = p.get("score") or {}
        if score.get("hard_constraint_violations"):
            lines.append(f"   ⚠ 硬约束违规：{score['hard_constraint_violations']}")
        if score.get("soft_constraint_violations"):
            lines.append(f"   · 软约束提醒：{score['soft_constraint_violations']}")
    lines.append("")
    rec = plans[0]
    lines.append(
        f"推荐方案 {rec['plan_id']}：在四米二使用率、装载率、趟次达成与成本之间取得最佳平衡。"
    )
    return "\n".join(lines)


def _build_chat_model():
    """按 settings 构造 OpenAI 兼容 Chat 模型（DeepSeek/OpenAI/通义千问）。"""
    from langchain_openai import ChatOpenAI

    if not settings.llm_api_key:
        raise RuntimeError("未配置 LLM API Key（SCHED_LLM_API_KEY 或 DEEPSEEK_API_KEY）")
    return ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        temperature=0.3,
        timeout=30,
        max_retries=1,
    )


async def explain_plan(plans: list[dict], state: dict | None = None) -> str:
    """生成方案比选的自然语言解释."""
    if not plans:
        return "未生成任何候选方案，请检查数据完整性或放宽约束。"

    if settings.llm_provider == "mock":
        return _mock_explain(plans)

    # 真实 LLM 调用
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        model = _build_chat_model()
        # 压缩方案数据供模型参考
        brief = "\n".join(
            f"{i}. {_format_plan_brief(p)}" for i, p in enumerate(plans, 1)
        )
        system = (
            "你是车辆智能调度助手，擅长物流配送方案的比选分析。"
            "请用中文输出专业的方案比选解释，300 字以内，"
            "对比各方案在装载率、四米二使用率、趟次达成、成本上的差异，并给出推荐理由。"
        )
        user = (
            f"本次调度共生成 {len(plans)} 个候选方案（已按综合评分降序排列）：\n{brief}\n\n"
            "请输出方案比选解释并推荐最优方案。"
        )
        resp = await model.ainvoke([SystemMessage(content=system), HumanMessage(content=user)])
        text = getattr(resp, "content", str(resp))
        return f"[由 {settings.llm_provider}/{settings.llm_model} 生成]\n{text}"
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM 调用失败，回退 mock 解释: %s", exc)
        return f"（LLM 调用失败：{exc}，已回退规则化解释）\n" + _mock_explain(plans)


async def _llm_report_summary(state: dict, selected: dict) -> str:
    """用 LLM 生成调度报告的自然语言总结段落。失败时返回空串。"""
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        model = _build_chat_model()
        system = "你是车辆智能调度助手，请用中文为调度报告生成一段 150 字以内的执行总结。"
        user = (
            f"任务 {state.get('task_id')}，日期 {state.get('schedule_date')}，"
            f"时段 {state.get('time_window')}，共 {len(state.get('scored_plans') or [])} 个候选方案。"
            f"选定方案 {selected.get('plan_id')}：总趟次 {selected.get('total_trips', 0)}，"
            f"用车 {selected.get('used_vehicles', 0)} 台，"
            f"平均装载率 {selected.get('avg_load_rate', 0):.2%}，"
            f"四米二使用率 {selected.get('four_two_usage', 0):.2%}，"
            f"估算成本 ¥{selected.get('estimated_cost', 0):.0f}。"
            f"异常重排次数 {state.get('replan_count', 0)}。"
        )
        resp = await model.ainvoke([SystemMessage(content=system), HumanMessage(content=user)])
        return getattr(resp, "content", str(resp))
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM 报告总结失败: %s", exc)
        return ""


async def generate_report(state: dict) -> tuple[str, dict]:
    """生成调度报告（自然语言 + 结构化指标）."""
    plans = state.get("scored_plans") or []
    selected = state.get("selected_plan") or (plans[0] if plans else None)
    confirmation = state.get("confirmation") or {}
    dispatch_result = state.get("dispatch_result") or {}
    replan_count = state.get("replan_count", 0)

    metrics: dict[str, Any] = {
        "task_id": state.get("task_id"),
        "schedule_date": state.get("schedule_date"),
        "time_window": state.get("time_window"),
        "rule_version": state.get("rule_version"),
        "candidate_count": len(plans),
        "selected_plan_id": confirmation.get("plan_id"),
        "dispatch_id": dispatch_result.get("dispatch_id"),
        "replan_count": replan_count,
        "llm_provider": settings.llm_provider,
    }
    if selected:
        metrics.update(
            {
                "total_trips": selected.get("total_trips", 0),
                "used_vehicles": selected.get("used_vehicles", 0),
                "avg_load_rate": selected.get("avg_load_rate", 0.0),
                "four_two_usage": selected.get("four_two_usage", 0.0),
                "big_small_achievement": selected.get("big_small_achievement", 0.0),
                "estimated_cost": selected.get("estimated_cost", 0.0),
            }
        )

    if selected is None:
        content = (
            f"调度任务 {state.get('task_id')} 在 {state.get('schedule_date')} 执行失败，"
            "未产生有效方案，请检查数据与规则配置。"
        )
        return content, metrics

    content = (
        f"【调度报告】任务 {state.get('task_id')}（{state.get('schedule_date')}）\n\n"
        f"1. 任务概况：调度日期 {state.get('schedule_date')}，时段 {state.get('time_window')}，"
        f"规则版本 {state.get('rule_version')}，共生成 {len(plans)} 个候选方案。\n\n"
        f"2. 选定方案：{selected.get('plan_id')}（{selected.get('name')}），"
        f"经调度员 {confirmation.get('operator', 'N/A')} 确认。\n\n"
        f"3. 执行指标：总趟次 {selected.get('total_trips', 0)}，"
        f"使用车辆 {selected.get('used_vehicles', 0)} 台，"
        f"平均装载率 {selected.get('avg_load_rate', 0):.2%}，"
        f"四米二使用率 {selected.get('four_two_usage', 0):.2%}，"
        f"大包/小包趟次达成率 {selected.get('big_small_achievement', 0):.2%}，"
        f"估算成本 ¥{selected.get('estimated_cost', 0):.0f}。\n\n"
        f"4. 下发结果：{dispatch_result.get('status', 'N/A')}，"
        f"dispatch_id={dispatch_result.get('dispatch_id', 'N/A')}。\n\n"
        f"5. 异常重排次数：{replan_count}。\n"
    )

    # 非 mock 时追加 LLM 总结
    if settings.llm_provider != "mock":
        summary = await _llm_report_summary(state, selected)
        if summary:
            content += f"\n6. AI 执行总结[由 {settings.llm_provider}/{settings.llm_model} 生成]：\n{summary}\n"

    return content, metrics
