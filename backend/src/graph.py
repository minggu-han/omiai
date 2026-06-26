"""LangGraph 状态图定义 —— AI 约会助攻顾问。

工作流：
    START → analyzer → generator → human_review [中断点]
                                        ├── accept ──→ refiner → simulator → END
                                        ├── modify ──→ refiner → simulator → END
                                        └── reject ──→ 重试次数<3? → generator
                                                       重试次数>=3? → END（强制退出）
"""

from typing import Optional

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.base import BaseCheckpointSaver

from src.state import OverallState
from src.nodes.analyzer import analyzer_node
from src.nodes.generator import generator_node
from src.nodes.refiner import refiner_node
from src.nodes.simulator import simulator_node


# ---------------------------------------------------------------------------
# 人工审核节点 —— 透传节点（实际的审核决策通过 update_state 传入）
# ---------------------------------------------------------------------------

def human_review_node(state: OverallState) -> dict:
    """人工审核透传节点。

    图在执行此节点之前会被中断。
    Streamlit UI 通过 `graph.update_state()` 将用户的审核决策
    写入状态，然后恢复执行。此节点本身仅做透传。
    """
    # 如果用户选择驳回，递增重试计数器
    decision = state.get("human_decision", "")
    if decision == "reject":
        return {"retry_count": state.get("retry_count", 0) + 1}

    return {}


# ---------------------------------------------------------------------------
# 条件路由
# ---------------------------------------------------------------------------

def route_after_review(state: OverallState) -> str:
    """根据人工审核结果决定下一步走向。

    返回值：
        "refiner"   — 用户接受或修改了候选回复，进入润色节点
        "generator" — 用户驳回，返回生成节点重新生成
        "end"       — 用户连续驳回 3 次以上，强制退出
    """
    decision = state.get("human_decision", "")
    retry = state.get("retry_count", 0)

    if decision == "reject":
        if retry >= 3:
            return "end"
        return "generator"

    # accept 或 modify → 进入润色节点
    return "refiner"


# ---------------------------------------------------------------------------
# 图构建器
# ---------------------------------------------------------------------------

def build_graph(checkpointer: Optional[BaseCheckpointSaver] = None):
    """构建并编译 AI 约会助攻顾问的 StateGraph。

    参数
    ----------
    checkpointer : BaseCheckpointSaver, optional
        LangGraph 检查点保存器。传入 None 时使用内存级 MemorySaver。
        生产环境传入 AsyncPostgresSaver 实现 PostgreSQL 持久化。

    返回一个已编译的图，配置了 interrupt_before=["human_review"] 中断点。
    """
    if checkpointer is None:
        checkpointer = MemorySaver()

    graph = StateGraph(OverallState)

    # --- 添加节点 ---
    graph.add_node("analyzer", analyzer_node)
    graph.add_node("generator", generator_node)
    graph.add_node("human_review", human_review_node)
    graph.add_node("refiner", refiner_node)
    graph.add_node("simulator", simulator_node)

    # --- 添加边 ---
    graph.add_edge(START, "analyzer")
    graph.add_edge("analyzer", "generator")

    # generator 之后进入 human_review（中断在此触发）
    graph.add_edge("generator", "human_review")

    # human_review 之后根据用户决策进行条件路由
    graph.add_conditional_edges(
        "human_review",
        route_after_review,
        {
            "refiner": "refiner",
            "generator": "generator",
            "end": END,
        },
    )

    graph.add_edge("refiner", "simulator")
    graph.add_edge("simulator", END)

    # --- 编译并配置中断 ---
    return graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_review"],
    )
