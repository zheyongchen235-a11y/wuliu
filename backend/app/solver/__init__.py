"""调度求解器。

混合求解策略：
- 阶段 1：启发式快速生成可行解（按地形/线路分组、按车型优先级派车）。
- 阶段 2：CP-SAT 局部优化（对四米二优先与装载率均衡方案做精确求解）。
- 阶段 3：多方案生成（A 四米二优先 / B 成本最低 / C 大包小包保障 / D 装载率均衡）。

入口：generate_plans(snapshot, config) -> list[dict]
"""
from .heuristic import generate_heuristic_plans
from .cpsat import generate_cpsat_plan
from .scorer import score_plan, rank_plans

__all__ = [
    "generate_heuristic_plans",
    "generate_cpsat_plan",
    "score_plan",
    "rank_plans",
    "generate_plans",
]


def generate_plans(snapshot: dict, config: dict | None = None) -> list[dict]:
    """生成多方案：A/B/C 启发式 + D CP-SAT 优化。

    snapshot: SchedulingTaskSnapshot 序列化字典
    config: 规则配置字典（hard/soft/weights）
    返回：方案字典列表，每个方案包含 details / metrics / score 字段
    """
    config = config or {}
    plans = generate_heuristic_plans(snapshot, config)
    # CP-SAT 方案 D：装载率均衡（优先装载率优化）
    cpsat_plan = generate_cpsat_plan(snapshot, config, strategy="load_balance")
    if cpsat_plan is not None:
        plans.append(cpsat_plan)
    # 对每个方案进行评分
    weights = config.get("weights") or {}
    for p in plans:
        p["score"] = score_plan(p, snapshot, weights)
    # 排序：评分降序
    plans = rank_plans(plans)
    return plans
