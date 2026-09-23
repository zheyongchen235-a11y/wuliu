"""LangGraph checkpointer.

简化实现：直接复用 MemorySaver 做运行时检查点。
生产环境可替换为 AsyncPostgresSaver / SqliteSaver。
"""
from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver


def make_checkpointer() -> MemorySaver:
    """构造 checkpointer 实例。"""
    return MemorySaver()
